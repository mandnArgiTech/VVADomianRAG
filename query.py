#!/usr/bin/env python3
"""
query.py — Terminal AI agent: hybrid RAG search (BM25 + dense + RRF), optional LLM chat,
stateful REPL, and rich terminal output. Standalone; does not import mcp_server.
"""
from __future__ import annotations

import argparse
import difflib
import json
import logging
import os
import re
import signal
import sys
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import readline
except ImportError:  # pragma: no cover
    readline = None  # type: ignore[assignment]

import chromadb
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings

from hybrid_search import (
    HYBRID_AVAILABLE,
    get_bm25_index,
    reciprocal_rank_fusion,
    search_bm25_ranked_ids,
    stable_doc_id,
)
from reranker import get_reranker, rerank_pool_limit

try:
    import ollama as _ollama_mod

    OLLAMA_LIB_AVAILABLE = True
except ImportError:  # pragma: no cover
    _ollama_mod = None  # type: ignore[assignment]
    OLLAMA_LIB_AVAILABLE = False

try:
    from rich.console import Console
    from rich.live import Live
    from rich.markdown import Markdown

    RICH_AVAILABLE = True
except ImportError:  # pragma: no cover
    Console = None  # type: ignore[misc, assignment]
    Live = None  # type: ignore[misc, assignment]
    Markdown = None  # type: ignore[misc, assignment]
    RICH_AVAILABLE = False

# ---------------------------------------------------------------------------
# Constants (aligned with mcp_server.py)
# ---------------------------------------------------------------------------

DIM_TO_MODEL = {
    1024: "mxbai-embed-large",
    768: "nomic-embed-text",
}

TOP_K_DEFAULT = int(os.environ.get("TOP_K", "5"))
MAX_K = max(1, int(os.environ.get("MCP_MAX_K", "25")))
RESULT_CHUNK_MAX_CHARS = max(512, int(os.environ.get("MCP_RESULT_CHUNK_MAX_CHARS", "4096")))
RESULT_CONTEXT_WINDOW_MAX_CHARS = max(
    RESULT_CHUNK_MAX_CHARS,
    int(os.environ.get("MCP_RESULT_CONTEXT_WINDOW_MAX_CHARS", "16000")),
)
DEFAULT_TIMEOUT = int(os.environ.get("QUERY_CLI_TIMEOUT", "120"))


def _metadata_pipe_or_comma_tokens(raw: str) -> List[str]:
    """Split ``calls`` / ``concepts``-style fields (pipe- or comma-delimited; matches ``ingest.iter_concept_ids``)."""
    s = (raw or "").strip()
    if not s:
        return []
    if s.startswith("|"):
        return [x.strip() for x in s.strip("|").split("|") if x.strip()]
    return [x.strip() for x in s.split(",") if x.strip()]
HISTORY_FILE = Path.home() / ".rag_query_history"

HYBRID_SEARCH = os.environ.get("HYBRID_SEARCH", "1").strip().lower() not in ("0", "false", "no")
RRF_K = float(os.environ.get("RRF_K", "60"))
RAG_CONTEXT_MAX_CHARS = max(4096, int(os.environ.get("RAG_CONTEXT_MAX_CHARS", "32000")))
# One Ollama embed_query for the whole multi-collection search (major latency win).
RAG_QUERY_SHARED_EMBED = os.environ.get("RAG_QUERY_SHARED_EMBED", "1").strip().lower() not in (
    "0",
    "false",
    "no",
)
# Dependency second-pass (see _sync_multi_search_with_dependency_hop)
QUERY_DEP_MAX_TOKENS = max(0, int(os.environ.get("QUERY_DEP_MAX_TOKENS", "16")))
QUERY_DEP_MAX_HITS = max(0, int(os.environ.get("QUERY_DEP_MAX_HITS", "10")))
QUERY_DEP_LOOKUP_K = max(1, int(os.environ.get("QUERY_DEP_LOOKUP_K", "2")))
QUERY_CALLER_MAX_HITS = max(0, int(os.environ.get("QUERY_CALLER_MAX_HITS", "10")))
# Dynamic system prompt from top-hit source types
QUERY_PROMPT_TOP_M = max(1, int(os.environ.get("QUERY_PROMPT_TOP_M", "5")))
QUERY_PROMPT_DOC_THRESHOLD = float(os.environ.get("QUERY_PROMPT_DOC_THRESHOLD", "0.6"))

# BM25 typo expansion: built at ingest time (see ingest.py symbols_vocabulary.json).
_vocab_cache: Dict[str, frozenset] = {}


def _load_symbols_vocab(db_path: str) -> frozenset:
    root = (db_path or "").strip()
    if not root:
        return frozenset()
    key = os.path.abspath(root)
    if key in _vocab_cache:
        return _vocab_cache[key]
    p = Path(key) / "symbols_vocabulary.json"
    if not p.is_file():
        _vocab_cache[key] = frozenset()
        return _vocab_cache[key]
    try:
        raw = json.loads(p.read_text(encoding="utf-8", errors="replace"))
        if isinstance(raw, list):
            vocab = frozenset(str(x) for x in raw if str(x).strip())
        elif isinstance(raw, dict) and "symbols" in raw:
            vocab = frozenset(str(x) for x in raw["symbols"] if str(x).strip())
        else:
            vocab = frozenset()
    except Exception:
        vocab = frozenset()
    _vocab_cache[key] = vocab
    return vocab


def _god_mode_chunk_name_matches(query_raw: str, vocab: frozenset) -> List[str]:
    """Build ``chunk_name`` values for Chroma ``$in`` God-mode (exact + case-insensitive vocab).

    Single-token queries also try the raw token when it is not already represented by a
    resolved canonical symbol (covers symbols missing from ``symbols_vocabulary.json``).
    """
    q = (query_raw or "").strip()
    if not q or not vocab:
        return []
    tokens = set(re.findall(r"[\w\.]+", q))
    canon_lower: Dict[str, str] = {v.lower(): v for v in vocab}
    out: List[str] = []
    seen: set = set()

    def add(name: str) -> None:
        n = (name or "").strip()
        if n and n not in seen:
            out.append(n)
            seen.add(n)

    for t in tokens:
        if t in vocab:
            add(t)
            continue
        c = canon_lower.get(t.lower())
        if c:
            add(c)

    if " " not in q:
        cq = canon_lower.get(q.lower())
        if q not in seen and (cq is None or cq not in seen):
            if q in vocab:
                add(q)
            elif cq:
                add(cq)
            else:
                add(q)
    return out


def _expand_query_typos(query: str, vocab: frozenset) -> str:
    if not vocab or not (query or "").strip():
        return query
    tokens = re.findall(r"[\w\.]+", query)
    vocab_lower_map = {v.lower(): v for v in vocab}
    expansions: List[str] = []
    for tok in tokens:
        if tok.lower() in vocab_lower_map:
            continue
        if len(tok) >= 4:
            matches = difflib.get_close_matches(tok.lower(), vocab_lower_map.keys(), n=1, cutoff=0.75)
            if matches:
                expansions.append(vocab_lower_map[matches[0]])
    if expansions:
        deduped = " ".join(dict.fromkeys(expansions))
        return query + " [Auto-expanded: " + deduped + "]"
    return query


def _persistent_chroma_client(path: str) -> chromadb.PersistentClient:
    """Chroma client with telemetry off (faster init, production hygiene)."""
    try:
        from chromadb.config import Settings

        return chromadb.PersistentClient(
            path=path,
            settings=Settings(anonymized_telemetry=False),
        )
    except Exception:
        return chromadb.PersistentClient(path=path)

# ---------------------------------------------------------------------------
# System prompt presets
# ---------------------------------------------------------------------------

_NGSPICE_SYSTEM_PROMPT = (
    "You are an expert ngspice / SPICE circuit simulator and C-codebase assistant "
    "with deep knowledge of the ngspice source tree, device model implementations, "
    "numerical methods (Newton-Raphson, GEAR integration), and the MNA matrix stamp API. "
    "Answer using ONLY the provided source-code context. "
    "When referencing code, quote the relevant lines and cite the exact file path. "
    "Prefer C function signatures and call-graph relationships in your explanations. "
    "State clearly when the context does not contain enough information to answer."
)

_GENERIC_SYSTEM_PROMPT = (
    "You are a Senior Engineering AI assistant with expertise in software architecture "
    "and code analysis. Answer the user's question using strictly the provided context. "
    "If the context does not contain enough information, say so clearly. "
    "Cite sources by file path or document name when possible. Be concise and precise."
)

_DEBUG_SYSTEM_PROMPT = (
    "You are a debugging specialist AI assistant. "
    "Analyse the provided code context for bugs, edge cases, and failure modes. "
    "For each finding state: (1) the problem, (2) the exact location (file + line reference), "
    "(3) a recommended fix. "
    "Only use information present in the provided context. "
    "Be systematic and complete — do not skip edge cases."
)

DEFAULT_SYSTEM_PROMPT = _GENERIC_SYSTEM_PROMPT

DEFAULT_SYSTEM_PROMPTS: Dict[str, str] = {
    "ngspice": _NGSPICE_SYSTEM_PROMPT,
    "generic": _GENERIC_SYSTEM_PROMPT,
    "debug": _DEBUG_SYSTEM_PROMPT,
}


def estimate_tokens(text: str, provider: str = "ollama") -> int:
    """Rough token count without a tokenizer: Claude averages ~4 chars/token, others ~3.5."""
    if not text:
        return 0
    divisor = 4.0 if provider == "anthropic" else 3.5
    return max(1, int(len(text) / divisor))

LANG_TAG = {
    ".py": "python",
    ".java": "java",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".jsx": "jsx",
    ".cs": "csharp",
    ".cpp": "cpp",
    ".c": "c",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".kt": "kotlin",
    ".scala": "scala",
    ".sql": "sql",
    ".sh": "bash",
    ".ps1": "powershell",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".json": "json",
    ".xml": "xml",
    ".html": "html",
    ".md": "markdown",
    ".proto": "protobuf",
    ".properties": "properties",
}

EXIT_OK = 0
EXIT_NO_RESULTS = 1
EXIT_ARG = 2
EXIT_INFRA = 3

log = logging.getLogger("query")


def _resolve_db_abs(db_path: str, cmap: Dict[str, Chroma]) -> str:
    if db_path.strip():
        return os.path.abspath(db_path)
    for vs in cmap.values():
        pd = getattr(vs, "_persist_directory", None) or getattr(vs, "persist_directory", None)
        if pd:
            return os.path.abspath(str(pd))
    return ""


def _hybrid_candidate_cap(k: int, env_var: str) -> int:
    raw = os.environ.get(env_var, "").strip()
    if raw.isdigit():
        return max(1, int(raw))
    return max(40, k * 4)


def _make_console(*, no_color: bool, file=None) -> Any:
    if not RICH_AVAILABLE or Console is None:
        return None
    return Console(no_color=no_color, file=file or sys.stdout)


def _print_rich(console: Any, text: str, *, use_markdown: bool = True) -> None:
    if console and RICH_AVAILABLE and Markdown is not None and use_markdown:
        console.print(Markdown(text))
    else:
        print(text)


def _status_spinner(console: Any, message: str) -> Any:
    if console and RICH_AVAILABLE:
        return console.status(message, spinner="dots")

    class _NoOp:
        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return False

    return _NoOp()


def _stream_chunk_text(chunk: Any) -> str:
    if chunk is None:
        return ""
    msg = getattr(chunk, "message", None)
    if msg is None and isinstance(chunk, dict):
        msg = chunk.get("message")
    if msg is None:
        return ""
    if isinstance(msg, dict):
        return str(msg.get("content") or "")
    return str(getattr(msg, "content", None) or "")


def embedding_model_from_db_path(db_path: str) -> str:
    """Resolve embedding model from on-disk DB config / Chroma dims only (no EMBEDDING_MODEL env).

    Use for ingestion paths that must match an existing VectorDB; ``detect_embedding_model`` still
    honors the env override first for query-time behavior.
    """
    config_path = os.path.join(db_path, "ingestion_config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, encoding="utf-8") as fh:
                model = json.load(fh).get("embedding_model", "")
            if model:
                return str(model).strip()
        except Exception:
            pass
    try:
        client = _persistent_chroma_client(db_path)
        cols = client.list_collections()
        if cols:
            col = client.get_collection(cols[0].name)
            rows = col.get(limit=1, include=["embeddings"])
            embs = rows.get("embeddings")
            if embs is not None and len(embs) > 0 and len(embs[0]) > 0:
                dim = len(embs[0])
                if dim in DIM_TO_MODEL:
                    return DIM_TO_MODEL[dim]
    except Exception:
        pass
    return "nomic-embed-text"


def detect_embedding_model(db_path: str) -> str:
    env_val = os.environ.get("EMBEDDING_MODEL", "").strip()
    if env_val:
        return env_val
    return embedding_model_from_db_path(db_path)


def check_ollama(timeout: float = 3.0) -> bool:
    try:
        urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=timeout)
        return True
    except Exception:
        return False


# Default chat LLM (STORY D). ``RAG_LLM_MODEL`` overrides when set in the environment.
DEFAULT_CHAT_LLM = "gemma3:27b-it-qat"
CHAT_MODEL_FALLBACKS = [
    "gemma3:27b-it-qat",
    "gemma3:27b",
    "gemma3:12b-it-qat",
    "gemma3:12b",
    "qwen2.5-coder:32b",
    "llama3",
    "mistral",
]


def default_chat_llm_from_env() -> str:
    env = (os.environ.get("RAG_LLM_MODEL", "") or "").strip()
    return env or DEFAULT_CHAT_LLM


def _ollama_base_url() -> str:
    return (os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")).rstrip("/")


def _load_system_prompt(domain: str, _prompts_dir: Optional[Path] = None) -> str:
    """Load ``system_prompts/{domain}_engineer.md``; if missing, ``default.md`` (AC-5).

    When ``domain`` is empty, returns ``""`` so base RAG personas are unchanged unless a domain
    is selected.

    ``_prompts_dir`` is the ``system_prompts`` directory (for tests); default is next to ``query.py``.
    """
    root = Path(__file__).resolve().parent
    sdir = _prompts_dir if _prompts_dir is not None else (root / "system_prompts")
    d = (domain or "").strip().lower()
    if not d:
        return ""
    p = sdir / f"{d}_engineer.md"
    if p.is_file():
        try:
            return p.read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            return ""
    p0 = sdir / "default.md"
    if p0.is_file():
        try:
            return p0.read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            return ""
    return ""


def _tag_matches_model(tag: str, want: str) -> bool:
    if not want or not tag:
        return False
    if tag == want or tag.startswith(want + ":"):
        return True
    if ":" not in want:
        return tag.split(":")[0] == want.split(":")[0]
    return False


def _pick_ollama_model_tag(names: List[str], want: str) -> str:
    for n in names:
        if n and _tag_matches_model(n, want):
            return n
    return ""


def _ollama_chat_model_names() -> List[str]:
    url = _ollama_base_url() + "/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read().decode())
    except Exception:
        return []
    models = data.get("models") or []
    return [str(m.get("name") or "") for m in models if m.get("name")]


def _check_model_available(model: str) -> str:
    """Return an Ollama tag that matches ``model`` if present; else first matching fallback tag."""
    log = logging.getLogger("query")
    names = _ollama_chat_model_names()
    want = (model or "").strip() or default_chat_llm_from_env()
    if not names:
        return want
    tag = _pick_ollama_model_tag(names, want)
    if tag:
        return tag
    log.warning(
        "Default model %s not found. Run: ollama pull %s",
        want,
        want.split(":")[0] if want else want,
    )
    for fb in CHAT_MODEL_FALLBACKS:
        tag = _pick_ollama_model_tag(names, fb)
        if tag:
            log.info("Falling back to Ollama model: %s", tag)
            return tag
    log.warning("No fallback model found in Ollama tags. Using %s anyway.", want)
    return want


def _ollama_options_for_model(model_name: str) -> Dict[str, Any]:
    """Ollama ``options`` for chat; Gemma gets larger context and repeat_penalty (STORY D / AC-6)."""
    tag = (model_name or "").lower()
    if "gemma" in tag:
        return {
            "num_ctx": 65536,
            "temperature": 0.1,
            "top_p": 0.9,
            "repeat_penalty": 1.1,
        }
    return {
        "num_ctx": 32768,
        "temperature": 0.2,
        "top_p": 0.95,
    }


def discover_collections(
    db_path: str,
    embeddings: OllamaEmbeddings,
    chroma_client: Optional[chromadb.PersistentClient] = None,
) -> Dict[str, Chroma]:
    """Open one PersistentClient and attach LangChain Chroma stores per collection.

    Reuses ``client`` for every ``Chroma`` wrapper (avoids a second sqlite open) and uses
    ``create_collection_if_not_exists=False`` so we only bind to existing collections — the
    default ``get_or_create`` path can misbehave across Chroma / LangChain versions when a DB
    already contains data.
    """
    out: Dict[str, Chroma] = {}
    log = logging.getLogger("query")
    try:
        client = chroma_client or _persistent_chroma_client(db_path)
        infos = client.list_collections()
    except Exception as exc:
        log.error("discover_collections: list_collections failed for %s: %s", db_path, exc)
        return out
    if not infos:
        log.warning(
            "discover_collections: list_collections() returned no collections for %s "
            "(folder may be empty or DB is locked by another process).",
            db_path,
        )
        return out
    for info in infos:
        name = info.name
        try:
            out[name] = Chroma(
                client=client,
                collection_name=name,
                embedding_function=embeddings,
                create_collection_if_not_exists=False,
            )
        except Exception as exc:
            log.error("discover_collections: failed to open collection %r: %s", name, exc)
    return out


def connect_chroma_with_retry(
    db_path: str,
    model: str,
) -> Tuple[chromadb.PersistentClient, OllamaEmbeddings, Dict[str, Chroma]]:
    import time

    log = logging.getLogger("query")
    last_exc: Optional[Exception] = None
    for attempt in range(3):
        try:
            client = _persistent_chroma_client(db_path)
            client.list_collections()
            embedder = OllamaEmbeddings(model=model)
            cmap = discover_collections(db_path, embedder, client)
            return client, embedder, cmap
        except Exception as exc:
            last_exc = exc
            log.warning("Chroma connect attempt %d failed: %s", attempt + 1, exc)
            time.sleep(2)
    raise RuntimeError(f"ChromaDB connection failed: {last_exc}")


def _infer_source_type(meta: Dict[str, Any]) -> str:
    st = (meta.get("source_type") or "").strip().lower()
    if st:
        return st
    cname = (meta.get("chunk_strategy") or "").lower()
    if "rfc" in cname:
        return "rfc"
    if "mib" in cname:
        return "mib"
    if "rally" in cname or meta.get("rally_id"):
        return "rally"
    if meta.get("ticket_id"):
        return "customer"
    if "wiki" in cname:
        return "wiki"
    if "community" in cname:
        return "community"
    if "release" in cname:
        return "release_notes"
    return "code"


def _fence_for(content: str) -> str:
    return "~~~" if "```" in content else "```"


def _truncate_chunk(text: str, max_chars: Optional[int] = None) -> str:
    """Truncate with newline / `}`-aware cut; close dangling ``` fences if needed."""
    mx = max_chars if max_chars is not None and max_chars > 0 else RESULT_CHUNK_MAX_CHARS
    if len(text) <= mx:
        return text
    suffix = "\n\n... (truncated for response size) ..."
    floor = min(mx, max(512, mx // 2))
    target_cut = mx - len(suffix)
    cut = max(floor, min(target_cut, len(text)))
    cut = min(cut, len(text))
    boundary = text.rfind("\n\n", 0, cut)
    if boundary < floor:
        boundary = text.rfind("\n", 0, cut)
    if boundary >= floor:
        cut = boundary
    else:
        brace = text.rfind("}", 0, cut)
        if brace >= floor:
            cut = brace + 1
    prefix = text[:cut]
    fence = "```"
    if prefix.count(fence) % 2 == 1:
        prefix = prefix + "\n" + fence
    return prefix + suffix


def format_result(doc: Any, score: Optional[float], source_type: str) -> str:
    """Prefer ``context_window`` over page_content; larger cap + syntax-aware ``_truncate_chunk``."""
    meta = doc.metadata or {}
    header: List[str] = []
    repo = meta.get("repository", "") or ""
    src = meta.get("relative_path", meta.get("source", "")) or ""
    cname = meta.get("chunk_name", "") or ""
    ctype = meta.get("chunk_type", "") or ""
    if score is not None:
        header.append(f"**Distance:** {score:.4f}")
    header.append(f"**source_type:** {source_type}")
    cw = (meta.get("context_window") or "").strip()
    if cw:
        raw_body = cw
        trunc_limit = RESULT_CONTEXT_WINDOW_MAX_CHARS
    else:
        raw_body = (doc.page_content or "").strip()
        trunc_limit = RESULT_CHUNK_MAX_CHARS
    content = _truncate_chunk(raw_body, trunc_limit)
    ext = (meta.get("extension") or "").lower()

    if source_type == "code":
        if repo:
            header.append(f"**Repo:** {repo}")
        header.append(f"**File:** {repo + '/' + src if repo else src}")
        if cname:
            header.append(f"**Component:** {cname} ({ctype})")
        dep = (meta.get("dependencies") or "").strip()
        if dep:
            dshow = dep if len(dep) <= 500 else dep[:500] + "…"
            header.append(f"**dependencies:** {dshow}")
        calls_str = (meta.get("calls") or "").strip()
        if calls_str:
            callees_list = [
                c for c in _metadata_pipe_or_comma_tokens(calls_str) if c != "__truncated__"
            ][:15]
            if callees_list:
                header.append(f"**Callees (Outgoing):** {', '.join(callees_list)}")
        if meta.get("retrieval_hop") == "caller":
            header.append("**[CALLER NODE]** This chunk calls the primary retrieved function.")
        lang = LANG_TAG.get(ext, "")
        fence = _fence_for(content)
        return "### Code\n" + "\n".join(header) + f"\n\n{fence}{lang}\n{content}\n{fence}"

    if source_type in ("domain_doc", "theory", "wiki"):
        sec = meta.get("section", meta.get("doc_title", "Domain Knowledge"))
        return f"### {sec}\n*Source: {meta.get('source', '')}*\n\n{content}"

    if source_type == "rfc":
        rfc = meta.get("rfc_number", "")
        sec = meta.get("section_number", "")
        st = meta.get("section_title", "")
        head = f"RFC {rfc} §{sec}"
        if st:
            head += f": {st}"
        return f"### {head}\n\n{content}"

    if source_type in ("rally", "customer"):
        tid = meta.get("rally_id", "") or meta.get("ticket_id", "")
        title = meta.get("chunk_name", "") or meta.get("Name", "")
        res = meta.get("has_resolution", "") == "true"
        line = f"[{tid}] {title}" if title else f"[{tid}]"
        if res:
            line += " — Resolution: (see body)"
        return f"### {line}\n\n{content}"

    if source_type == "mib":
        oid = meta.get("object_name", "")
        path = meta.get("oid_path", "")
        return f"### OID: {oid} ({path}) — Description\n\n{content}"

    if source_type == "community":
        plat = meta.get("source_platform", "unknown")
        return f"### Source: [{plat}] — {meta.get('source_url', '')}\n\n{content}"

    return "### Result\n" + "\n".join(header) + f"\n\n{content}"


def _domain_filter(names: List[str], domain: str) -> List[str]:
    d = domain.strip().lower()
    if not d or d == "general":
        return names
    return [n for n in names if n.lower().startswith(d + "_") or n.lower() == d]


def _select_collection_names(cmap: Dict[str, Chroma], search_type: str, domain: str) -> List[str]:
    names = list(cmap.keys())
    names = _domain_filter(names, domain)
    st = search_type.lower().strip()
    if st == "auto" or not st:
        return names
    if st == "code":
        return [n for n in names if n.endswith("_code")]
    if st == "domain":
        return [n for n in names if "_domain" in n or n == "theory"]
    if st == "troubleshoot":
        return [
            n
            for n in names
            if any(x in n for x in ("_domain", "community", "_customer", "_internal"))
        ]
    if st == "reference":
        return [n for n in names if n == "rfc" or n == "theory" or "_mib" in n or n.endswith("_releases")]
    return names


@dataclass
class SearchHit:
    content: str
    score: Optional[float]
    source_type: str
    metadata: Dict[str, Any]
    collection: Optional[str] = None
    retrieval_hop: Optional[str] = None


def _shared_query_embedding(cmap: Dict[str, Chroma], targets: List[str], query: str) -> Optional[List[float]]:
    """Single embed_query for all collections (same model / vector space)."""
    if not RAG_QUERY_SHARED_EMBED or not targets or not (query or "").strip():
        return None
    vs0 = cmap.get(targets[0])
    if vs0 is None:
        return None
    emb_fn = getattr(vs0, "_embedding_function", None)
    if emb_fn is None:
        return None
    try:
        vec = emb_fn.embed_query(query)
        return list(vec) if vec is not None else None
    except Exception as exc:
        log.debug("shared embed_query failed, using per-query embedding: %s", exc)
        return None


def _similarity_search_with_score_efficient(
    vs: Any,
    query: str,
    k: int,
    flt: Optional[Dict[str, str]],
    q_emb: Optional[List[float]],
) -> List[Tuple[Any, Any]]:
    """Dense search: reuse precomputed embedding when LangChain Chroma supports it."""
    if q_emb is not None:
        fn = getattr(vs, "similarity_search_by_vector_with_relevance_scores", None)
        if callable(fn):
            try:
                return fn(q_emb, k=k, filter=flt)
            except TypeError:
                try:
                    return fn(q_emb, k, flt)
                except Exception:
                    pass
            except Exception as exc:
                log.debug("similarity_search_by_vector_with_relevance_scores failed: %s", exc)
    try:
        if flt is not None:
            return vs.similarity_search_with_score(query, k=k, filter=flt)
        return vs.similarity_search_with_score(query, k=k)
    except TypeError:
        return vs.similarity_search_with_score(query, k=k)


def _exact_chunk_name_hits(
    query_raw: str,
    targets: List[str],
    cmap: Dict[str, Chroma],
    repo_filter: str,
    vocab: frozenset,
) -> List[SearchHit]:
    """Fast metadata pre-fetch: chunk_names from ``_god_mode_chunk_name_matches``."""
    matches = _god_mode_chunk_name_matches(query_raw, vocab)
    if not matches:
        return []
    chroma_limit = min(512, max(8, len(matches) * 8))
    exact: List[SearchHit] = []
    seen: set = set()
    rf = repo_filter.strip()
    for name in targets:
        vs = cmap.get(name)
        if vs is None:
            continue
        col = getattr(vs, "_collection", None)
        if col is None:
            continue
        try:
            # Chroma expects structured operators (e.g. $in, $eq); bare {"chunk_name": q} is unreliable.
            res = col.get(
                where={"chunk_name": {"$in": matches}},
                limit=chroma_limit,
                include=["documents", "metadatas"],
            )
        except Exception as exc:
            log.debug("exact chunk_name lookup failed on %s: %s", name, exc)
            continue
        docs = res.get("documents") or []
        metas = res.get("metadatas") or []
        ids_list = res.get("ids") or []
        for i in range(len(docs)):
            text = docs[i] if i < len(docs) else ""
            meta = dict(metas[i] if i < len(metas) else {})
            did = ids_list[i] if i < len(ids_list) else ""
            key = did or stable_doc_id(name, meta, text)
            if key in seen:
                continue
            if rf and str(meta.get("repository", "")).strip() != rf:
                continue
            seen.add(key)
            st = _infer_source_type(meta)
            meta["_exact_match"] = "chunk_name"
            exact.append(
                SearchHit(content=text, score=0.0, source_type=st, metadata=meta, collection=name)
            )
    return exact


def _sync_multi_search(
    query: str,
    k: int,
    search_type: str,
    domain: str,
    repo_filter: str,
    cmap: Dict[str, Chroma],
    db_path: str = "",
    min_score_threshold: float = 0.0,
) -> List[SearchHit]:
    """Retrieve up to k chunks using dense or hybrid (RRF) search.

    Args:
        min_score_threshold: For dense-only mode, discard hits whose distance
            score exceeds this value (higher distance = less similar in
            cosine-distance space).  0.0 disables the filter.
    """
    db_abs_for_vocab = _resolve_db_abs(db_path, cmap)
    vocab = _load_symbols_vocab(db_abs_for_vocab)
    query = _expand_query_typos(query, vocab)
    if not cmap:
        raise RuntimeError("ChromaDB has no collections.")
    targets = _select_collection_names(cmap, search_type, domain)
    # --- God Mode: exact chunk_name pre-fetch (bypasses all scoring) ---
    exact_hits = _exact_chunk_name_hits(query, targets, cmap, repo_filter, vocab)
    exact_seen = {stable_doc_id(h.collection or "", h.metadata, h.content) for h in exact_hits}
    per = max(1, k // max(1, len(targets)) if targets else k)
    q_emb = _shared_query_embedding(cmap, targets, query)
    use_hybrid = HYBRID_SEARCH and HYBRID_AVAILABLE and bool(_resolve_db_abs(db_path, cmap))
    if HYBRID_SEARCH and not HYBRID_AVAILABLE:
        log.warning(
            "HYBRID_SEARCH is on but rank-bm25 is not installed; using dense-only. pip install rank-bm25"
        )

    def _hit(doc: Any, score: Optional[float], st: str, cname: str) -> SearchHit:
        return SearchHit(
            content=doc.page_content or "",
            score=float(score) if score is not None else None,
            source_type=st,
            metadata=dict(doc.metadata or {}),
            collection=cname,
        )

    if not use_hybrid:
        merged: List[Tuple[Any, Optional[float], str, str]] = []
        for name in targets:
            vs = cmap[name]
            flt: Optional[Dict[str, str]] = None
            if repo_filter.strip():
                flt = {"repository": repo_filter.strip()}
            try:
                pairs = _similarity_search_with_score_efficient(vs, query, per, flt, q_emb)
            except Exception as exc:
                log.warning("Skipping collection %s: %s", name, exc)
                continue
            for doc, score in pairs:
                meta = doc.metadata or {}
                st = _infer_source_type(meta)
                if search_type.lower() == "troubleshoot":
                    ct = (meta.get("content_type") or "").lower()
                    if ct not in ("edge_case", "workaround", "bug_report"):
                        continue
                merged.append((doc, score, st, name))
        merged.sort(key=lambda x: x[1] if x[1] is not None else 1e9)
        # Optionally discard low-relevance hits (high distance = low similarity)
        if min_score_threshold > 0:
            merged = [(d, s, st, cn) for d, s, st, cn in merged if s is None or s <= min_score_threshold]
        regular = [
            _hit(doc, score, st, cn) for doc, score, st, cn in merged[:rerank_pool_limit(k)]
            if stable_doc_id(cn, doc.metadata or {}, doc.page_content) not in exact_seen
        ]
        _reranker = get_reranker()
        if _reranker is not None and regular:
            _cand_count = int(os.environ.get("RAG_RERANKER_CANDIDATES", "30"))
            _to_rerank = regular[:_cand_count]
            _texts = [h.content for h in _to_rerank]
            _ranked = _reranker.rerank(query, _texts, top_k=k)
            regular = [_to_rerank[idx] for idx, _score in _ranked]
        return exact_hits + regular

    db_abs = _resolve_db_abs(db_path, cmap)
    dense_cap = _hybrid_candidate_cap(k, "HYBRID_DENSE_CANDIDATES")
    bm25_cap = _hybrid_candidate_cap(k, "HYBRID_BM25_CANDIDATES")
    fused: List[Tuple[Any, Optional[float], str, str, float]] = []

    for name in targets:
        vs = cmap[name]
        flt: Optional[Dict[str, str]] = None
        if repo_filter.strip():
            flt = {"repository": repo_filter.strip()}
        try:
            pairs = _similarity_search_with_score_efficient(vs, query, dense_cap, flt, q_emb)
        except Exception as exc:
            log.warning("Skipping collection %s: %s", name, exc)
            continue

        dense_ids: List[str] = []
        dense_map: Dict[str, Tuple[Any, float]] = {}
        for doc, score in pairs:
            sid = stable_doc_id(name, doc.metadata or {}, doc.page_content)
            dense_ids.append(sid)
            dense_map[sid] = (doc, score)

        bm25_ids: List[str] = []
        col = getattr(vs, "_collection", None)
        if col is not None and db_abs:
            idx = get_bm25_index(db_abs, name)
            if idx.ensure_loaded(col):
                bm25_ids = search_bm25_ranked_ids(idx, query, bm25_cap, repo_filter)
        rank_lists = [dense_ids, bm25_ids] if bm25_ids else [dense_ids]
        rrf_scores = reciprocal_rank_fusion(rank_lists, k=RRF_K)
        if not rrf_scores:
            continue

        bm25_rank = {sid: r for r, sid in enumerate(bm25_ids)}
        dense_rank = {sid: r for r, sid in enumerate(dense_ids)}
        sorted_sids = sorted(
            rrf_scores.keys(),
            key=lambda sid: (
                -rrf_scores[sid],
                bm25_rank.get(sid, 10**9),
                dense_rank.get(sid, 10**9),
            ),
        )
        idx_ref = get_bm25_index(db_abs, name) if col is not None else None
        for sid in sorted_sids:
            if sid in dense_map:
                doc, _dscore = dense_map[sid]
            elif idx_ref is not None and sid in idx_ref.id_to_doc:
                text, meta = idx_ref.id_to_doc[sid]
                doc = Document(page_content=text, metadata=meta)
            else:
                continue
            meta = doc.metadata or {}
            st = _infer_source_type(meta)
            if search_type.lower() == "troubleshoot":
                ct = (meta.get("content_type") or "").lower()
                if ct not in ("edge_case", "workaround", "bug_report"):
                    continue
            fused.append((doc, None, st, name, rrf_scores[sid]))

    fused.sort(key=lambda x: x[4], reverse=True)
    regular = [
        _hit(doc, score, st, cn) for doc, score, st, cn, _ in fused[:rerank_pool_limit(k)]
        if stable_doc_id(cn, doc.metadata or {}, doc.page_content) not in exact_seen
    ]
    _reranker = get_reranker()
    if _reranker is not None and regular:
        _cand_count = int(os.environ.get("RAG_RERANKER_CANDIDATES", "30"))
        _to_rerank = regular[:_cand_count]
        _texts = [h.content for h in _to_rerank]
        _ranked = _reranker.rerank(query, _texts, top_k=k)
        regular = [_to_rerank[idx] for idx, _score in _ranked]
    return exact_hits + regular


def _parse_dependency_tokens(deps: str) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for part in (deps or "").split(","):
        t = part.strip()
        if not t or t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out


def _fused_docs_for_query_text(
    name: str,
    vs: Any,
    query_text: str,
    db_abs: str,
    repo_filter: str,
    search_type: str,
    cmap: Dict[str, Chroma],
    k_out: int,
    use_hybrid: bool,
    *,
    skip_troubleshoot_gate: bool = False,
) -> List[Tuple[Any, Optional[float]]]:
    """Dense or hybrid (RRF) retrieval for a single query string in one collection."""
    if k_out <= 0:
        return []
    flt: Optional[Dict[str, str]] = None
    if repo_filter.strip():
        flt = {"repository": repo_filter.strip()}
    q_emb = _shared_query_embedding(cmap, [name], query_text)

    def _passes_tt(meta: Dict[str, Any]) -> bool:
        if skip_troubleshoot_gate or search_type.lower() != "troubleshoot":
            return True
        ct = (meta.get("content_type") or "").lower()
        return ct in ("edge_case", "workaround", "bug_report")

    if not use_hybrid:
        pairs = _similarity_search_with_score_efficient(
            vs, query_text, max(k_out * 3, 8), flt, q_emb
        )
        out: List[Tuple[Any, Optional[float]]] = []
        for doc, score in pairs:
            if not _passes_tt(doc.metadata or {}):
                continue
            out.append((doc, float(score) if score is not None else None))
            if len(out) >= k_out:
                break
        return out

    dense_cap = _hybrid_candidate_cap(max(k_out, 4), "HYBRID_DENSE_CANDIDATES")
    bm25_cap = _hybrid_candidate_cap(max(k_out, 4), "HYBRID_BM25_CANDIDATES")
    pairs = _similarity_search_with_score_efficient(vs, query_text, dense_cap, flt, q_emb)
    dense_ids: List[str] = []
    dense_map: Dict[str, Tuple[Any, float]] = {}
    for doc, score in pairs:
        sid = stable_doc_id(name, doc.metadata or {}, doc.page_content)
        dense_ids.append(sid)
        dense_map[sid] = (doc, score)

    bm25_ids: List[str] = []
    col = getattr(vs, "_collection", None)
    if col is not None and db_abs:
        idx = get_bm25_index(db_abs, name)
        if idx.ensure_loaded(col):
            bm25_ids = search_bm25_ranked_ids(idx, query_text, bm25_cap, repo_filter)
    rank_lists = [dense_ids, bm25_ids] if bm25_ids else [dense_ids]
    rrf_scores = reciprocal_rank_fusion(rank_lists, k=RRF_K)
    if not rrf_scores:
        return []
    sorted_sids = sorted(rrf_scores.keys(), key=lambda sid: -rrf_scores[sid])
    idx_ref = get_bm25_index(db_abs, name) if col is not None else None
    out2: List[Tuple[Any, Optional[float]]] = []
    for sid in sorted_sids:
        if sid in dense_map:
            doc, sc = dense_map[sid]
        elif idx_ref is not None and sid in idx_ref.id_to_doc:
            text, meta = idx_ref.id_to_doc[sid]
            doc = Document(page_content=text, metadata=meta)
            sc = None
        else:
            continue
        if not _passes_tt(doc.metadata or {}):
            continue
        out2.append((doc, float(sc) if sc is not None else None))
        if len(out2) >= k_out:
            break
    return out2


def _depend_stems_from_results(
    results: List[Tuple[Any, Optional[float], str]],
) -> List[str]:
    stems: set = set()
    for doc, _, _ in results:
        meta = getattr(doc, "metadata", None) or {}
        rel = str(meta.get("relative_path") or "").strip()
        if rel:
            stem = Path(rel).stem
            if stem:
                stems.add(stem)
            stems.add(Path(rel.replace("\\", "/")).name)
        cn = str(meta.get("chunk_name") or "").strip()
        if cn:
            stems.add(cn)
    return sorted(stems)


def _dependencies_where_comma_token(stem: str) -> Dict[str, Any]:
    """Match *stem* as a whole entry in comma-separated ``dependencies`` metadata."""
    s = (stem or "").strip()
    if not s:
        return {"dependencies": {"$eq": "__empty_dependency_stem__"}}
    return {
        "$or": [
            {"dependencies": {"$eq": s}},
            {"dependencies": {"$contains": f"{s}, "}},
            {"dependencies": {"$contains": f", {s}, "}},
            {"dependencies": {"$contains": f", {s}"}},
        ]
    }


def _sync_fetch_dependents(
    primary: List[Tuple[Any, Optional[float], str]],
    search_type: str,
    domain: str,
    repo_filter: str,
    cmap: Dict[str, Chroma],
    max_hits: int,
) -> List[Tuple[Any, Optional[float], str, str]]:
    """Chunks whose *dependencies* metadata references symbols from primary hits.

    Returns ``(doc, score, source_type, collection_name)`` for stable dedupe / SearchHit.
    """
    targets = _select_collection_names(cmap, search_type, domain)
    lookups = _depend_stems_from_results(primary)
    if not lookups or not targets:
        return []
    seen: set = set()
    out: List[Tuple[Any, Optional[float], str, str]] = []
    rf = repo_filter.strip()
    for stem in lookups:
        if not stem:
            continue
        where_dep = _dependencies_where_comma_token(stem)
        for name in targets:
            vs = cmap[name]
            col = getattr(vs, "_collection", None)
            if col is None:
                continue
            try:
                res = col.get(
                    where=where_dep,
                    limit=40,
                    include=["documents", "metadatas"],
                )
            except Exception as exc:
                log.warning("dependents get failed on %s: %s", name, exc)
                continue
            ids_list = res.get("ids") or []
            docs = res.get("documents") or []
            metas = res.get("metadatas") or []
            for i, did in enumerate(ids_list):
                if did in seen:
                    continue
                meta = metas[i] if i < len(metas) else {}
                if rf and str((meta or {}).get("repository", "")).strip() != rf:
                    continue
                seen.add(did)
                text = docs[i] if i < len(docs) else ""
                doc = Document(page_content=text or "", metadata=dict(meta or {}))
                st = _infer_source_type(meta or {})
                out.append((doc, None, st, name))
                if len(out) >= max_hits:
                    return out
    return out


def _sync_fetch_callers(
    primary: List[SearchHit],
    search_type: str,
    domain: str,
    repo_filter: str,
    cmap: Dict[str, Chroma],
    max_hits: int,
) -> List[Tuple[Any, Optional[float], str, str]]:
    """Fetch chunks that call functions found in primary hits (reverse call-graph hop).

    For each primary code hit with a ``chunk_name``, queries code collections for
    chunks whose ``calls`` metadata contains ``|chunk_name|``.
    Returns ``(doc, score, source_type, collection_name)`` tuples.
    """
    code_names = _select_collection_names(cmap, search_type, domain)
    rf = repo_filter.strip()
    seen: set = set()
    out: List[Tuple[Any, Optional[float], str, str]] = []
    for hit in primary:
        if hit.source_type != "code":
            continue
        chunk_name = str((hit.metadata or {}).get("chunk_name") or "").strip()
        if not chunk_name:
            continue
        needle = f"|{chunk_name}|"
        for coll_name in code_names:
            if len(out) >= max_hits:
                return out
            vs = cmap[coll_name]
            col = getattr(vs, "_collection", None)
            if col is None:
                continue
            try:
                res = col.get(
                    where={"calls": {"$contains": needle}},
                    limit=5,
                    include=["documents", "metadatas"],
                )
            except Exception as exc:
                log.warning("caller get failed on %s: %s", coll_name, exc)
                continue
            ids_list = res.get("ids") or []
            docs_list = res.get("documents") or []
            metas_list = res.get("metadatas") or []
            for i, did in enumerate(ids_list):
                if did in seen:
                    continue
                meta = metas_list[i] if i < len(metas_list) else {}
                if rf and str((meta or {}).get("repository", "")).strip() != rf:
                    continue
                seen.add(did)
                text = docs_list[i] if i < len(docs_list) else ""
                doc = Document(page_content=text or "", metadata=dict(meta or {}))
                st = _infer_source_type(meta or {})
                out.append((doc, None, st, coll_name))
                if len(out) >= max_hits:
                    return out
    return out


def _sync_multi_search_with_dependency_hop(
    query: str,
    k: int,
    search_type: str,
    domain: str,
    repo_filter: str,
    cmap: Dict[str, Chroma],
    db_path: str = "",
    min_score_threshold: float = 0.0,
) -> List[SearchHit]:
    """Primary search plus Chroma ``dependencies`` metadata lookup (headers / related chunks)."""
    primary = _sync_multi_search(
        query, k, search_type, domain, repo_filter, cmap, db_path, min_score_threshold
    )
    if QUERY_DEP_MAX_HITS <= 0 or not primary:
        return primary

    primary_tuples: List[Tuple[Any, Optional[float], str]] = [
        (Document(page_content=h.content, metadata=dict(h.metadata or {})), h.score, h.source_type)
        for h in primary
    ]
    dep_tuples = _sync_fetch_dependents(
        primary_tuples,
        search_type,
        domain,
        repo_filter,
        cmap,
        max_hits=min(k * 2, max(1, QUERY_DEP_MAX_HITS * 2)),
    )
    seen = {stable_doc_id(h.collection or "", h.metadata, h.content) for h in primary}
    extra: List[SearchHit] = []
    for doc, _sc, st, cname in dep_tuples:
        sid = stable_doc_id(cname, doc.metadata or {}, doc.page_content or "")
        if sid in seen:
            continue
        seen.add(sid)
        meta = dict(doc.metadata or {})
        meta["retrieval_hop"] = "dependency"
        extra.append(
            SearchHit(
                content=doc.page_content or "",
                score=None,
                source_type=st,
                metadata=meta,
                collection=cname,
                retrieval_hop="dependency",
            )
        )

    if QUERY_CALLER_MAX_HITS > 0:
        caller_tuples = _sync_fetch_callers(
            primary,
            search_type,
            domain,
            repo_filter,
            cmap,
            max_hits=QUERY_CALLER_MAX_HITS,
        )
        for doc, _sc, st, cname in caller_tuples:
            sid = stable_doc_id(cname, doc.metadata or {}, doc.page_content or "")
            if sid in seen:
                continue
            seen.add(sid)
            meta = dict(doc.metadata or {})
            meta["retrieval_hop"] = "caller"
            extra.append(
                SearchHit(
                    content=doc.page_content or "",
                    score=None,
                    source_type=st,
                    metadata=meta,
                    collection=cname,
                    retrieval_hop="caller",
                )
            )

    return primary + extra


def _effective_system_prompt(
    hits: List[SearchHit],
    search_type: str,
    override: Optional[str],
    domain: str = "",
) -> str:
    """Pick ngspice vs generic vs debug persona from top-hit source types unless user overrode.

    When ``domain`` is set and ``system_prompts/{domain}_engineer.md`` (or ``default.md``) exists,
    that text is prepended (AC-4).
    """
    if override is not None:
        return override
    if not hits:
        base = DEFAULT_SYSTEM_PROMPT
    else:
        m = min(QUERY_PROMPT_TOP_M, len(hits))
        docish = {"rally", "customer", "community"}
        cnt = sum(1 for h in hits[:m] if h.source_type in docish)
        if m > 0 and cnt / m >= QUERY_PROMPT_DOC_THRESHOLD:
            if search_type.lower() == "troubleshoot":
                base = _DEBUG_SYSTEM_PROMPT
            else:
                base = _GENERIC_SYSTEM_PROMPT
        else:
            base = _GENERIC_SYSTEM_PROMPT
    dp = (_load_system_prompt(domain) or "").strip()
    if dp:
        return f"{dp}\n\n---\n\n{base}"
    return base


def _concept_parts(concepts_field: str) -> List[str]:
    s = (concepts_field or "").strip()
    if not s:
        return []
    if s.startswith("|"):
        return [x.strip() for x in s.strip("|").split("|") if x.strip()]
    return [x.strip() for x in s.split(",") if x.strip()]


def concept_search_hits(concept: str, domain: str, cmap: Dict[str, Chroma]) -> List[SearchHit]:
    concept = concept.strip()
    if not concept:
        return []
    safe_concept = concept.replace("|", "")
    if not safe_concept:
        return []
    needle = f"|{safe_concept}|"
    hits: List[SearchHit] = []
    for cname, vs in cmap.items():
        if domain and not _domain_filter([cname], domain):
            continue
        try:
            col = vs._collection  # type: ignore[attr-defined]
            res = col.get(
                where={"concepts": {"$contains": needle}},
                limit=80,
                include=["documents", "metadatas"],
            )
            if not (res.get("ids") or []):
                res = col.get(
                    where={"concepts": {"$contains": safe_concept}},
                    limit=80,
                    include=["documents", "metadatas"],
                )
            ids_list = res.get("ids") or []
            docs = res.get("documents") or []
            metas = res.get("metadatas") or []
            for i, _did in enumerate(ids_list):
                text = docs[i] if i < len(docs) else ""
                meta = metas[i] if i < len(metas) else {}
                st = _infer_source_type(meta or {})
                hits.append(
                    SearchHit(
                        content=text or "",
                        score=None,
                        source_type=st,
                        metadata=dict(meta or {}),
                        collection=cname,
                    )
                )
        except Exception as exc:
            logging.getLogger("query").warning("concept query failed on %s: %s", cname, exc)
    return hits


def _safe_count(coll: Any) -> int:
    try:
        return int(coll.count())
    except Exception:
        return 0


def run_status(db_path: str) -> str:
    from collections import Counter

    lines: List[str] = []
    lines.append("=" * 64)
    lines.append("            DOMAIN RAG — KNOWLEDGE BASE STATUS")
    lines.append("=" * 64)
    client = _persistent_chroma_client(db_path)
    cols = client.list_collections()
    concept_counts: Counter[str] = Counter()
    rows = []
    for c in sorted(cols, key=lambda x: x.name):
        coll = client.get_collection(c.name)
        n = _safe_count(coll)
        if n == 0:
            rows.append((c.name, 0, 0, ""))
            continue
        sample = coll.get(include=["metadatas"], limit=min(n, 8000))
        metas = sample.get("metadatas") or []
        sources = {str(m.get("source", "")) for m in metas if m}
        for m in metas:
            if not m:
                continue
            cs = m.get("concepts", "")
            if cs:
                for part in _concept_parts(str(cs)):
                    concept_counts[part] += 1
        dates = [str(m.get("ingestion_date", "")) for m in metas if m and m.get("ingestion_date")]
        last_ing = max(dates) if dates else ""
        rows.append((c.name, n, len(sources), last_ing))
    hdr = f"{'Collection':<22} {'Chunks':>8} {'Sources':>8} {'Last Ingested':<22}"
    lines.append(hdr)
    lines.append("-" * 64)
    for name, n, sc, li in rows:
        lines.append(f"{name:<22} {n:>8,} {sc:>8} {li:<22}")
    lines.append("=" * 64)
    top = concept_counts.most_common(15)
    if top:
        lines.append("Top concepts: " + ", ".join(f"{k}({v})" for k, v in top))
    return "\n".join(lines)


def run_with_timeout(seconds: int, fn, *args, **kwargs):
    if seconds <= 0:
        return fn(*args, **kwargs)
    if not hasattr(signal, "SIGALRM"):
        return fn(*args, **kwargs)

    def handler(_signum, _frame):
        raise TimeoutError(f"Query timed out after {seconds}s")

    old = signal.signal(signal.SIGALRM, handler)
    try:
        signal.alarm(max(1, int(seconds)))
        return fn(*args, **kwargs)
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)


def format_markdown(hits: List[SearchHit], query: str) -> str:
    if not hits:
        return "No matching chunks found."
    fake_docs = []
    for h in hits:
        doc = type("D", (), {"page_content": h.content, "metadata": h.metadata})()
        fake_docs.append(format_result(doc, h.score, h.source_type))
    return "\n\n---\n\n".join(fake_docs)


def format_concept_markdown(hits: List[SearchHit], concept: str) -> str:
    if not hits:
        return f"No chunks tagged with concept '{concept}'."
    by_st: Dict[str, List[str]] = {}
    for h in hits:
        doc = type("D", (), {"page_content": h.content, "metadata": h.metadata})()
        formatted = format_result(doc, None, h.source_type)
        cname = h.collection or ""
        by_st.setdefault(h.source_type, []).append(f"*({cname})* {formatted}")
    parts = []
    for st in sorted(by_st.keys()):
        parts.append(f"## source_type: **{st}**")
        parts.extend(by_st[st])
    return "\n\n".join(parts)


def format_json_output(
    query: str, hits: List[SearchHit], mode: str, answer: str = ""
) -> str:
    payload: Dict[str, Any] = {
        "query": query,
        "mode": mode,
        "results": [asdict(h) for h in hits],
    }
    if answer:
        payload["answer"] = answer
    return json.dumps(payload, indent=2)


def format_plain(hits: List[SearchHit]) -> str:
    if not hits:
        return ""
    blocks = []
    for h in hits:
        head = f"[{h.source_type}]"
        if h.collection:
            head += f" ({h.collection})"
        if h.score is not None:
            head += f" score={h.score:.4f}"
        src = h.metadata.get("relative_path") or h.metadata.get("source", "")
        blocks.append(f"{head}\n{src}\n{h.content[:RESULT_CHUNK_MAX_CHARS]}")
    return "\n\n---\n\n".join(blocks)


def _build_context_blocks(hits: List[SearchHit], max_chars: Optional[int] = None) -> str:
    """Build the RAG context string for the LLM prompt.

    Phase-5: prefers ``context_window`` metadata over chunk body; ``_truncate_chunk`` is
    syntax-aware (newlines / fences) so prompts stay well-formed.

    Args:
        hits: Retrieved chunks in ranked order.
        max_chars: Character budget (defaults to RAG_CONTEXT_MAX_CHARS env default).
                   Pass a provider-specific value for larger context windows.
    """
    budget = max_chars if max_chars and max_chars > 0 else RAG_CONTEXT_MAX_CHARS
    blocks: List[str] = []
    total = 0
    for i, h in enumerate(hits, 1):
        meta = h.metadata or {}
        # Prefer relative_path then absolute source; shorten very long paths
        src_raw = meta.get("relative_path") or meta.get("source", "?")
        src = src_raw if len(src_raw) <= 120 else "…/" + "/".join(str(src_raw).split("/")[-3:])
        # Enrich label with chunk_name and chunk_type when available
        cname = meta.get("chunk_name", "")
        ctype = meta.get("chunk_type", "")
        label_extras = ""
        if cname:
            label_extras += f" | {cname}"
        if ctype:
            label_extras += f" [{ctype}]"
        raw_body = (meta.get("context_window") or "").strip() or h.content
        body = _truncate_chunk(raw_body)
        block = f"[Source {i}: {src} ({h.source_type}){label_extras}]\n{body}"
        if total + len(block) > budget:
            remaining = len(hits) - i + 1
            blocks.append(f"\n[... {remaining} more chunk(s) omitted — context budget {budget:,} chars reached]")
            break
        blocks.append(block)
        total += len(block)
    return "\n\n---\n\n".join(blocks)


def _collect_llm_answer(
    user_query: str,
    hits: List[SearchHit],
    llm_model: str,
    system_prompt: str,
    history_messages: Optional[List[Dict[str, str]]] = None,
) -> str:
    if not OLLAMA_LIB_AVAILABLE or _ollama_mod is None:
        print("Warning: ollama package not installed; skipping LLM answer.", file=sys.stderr)
        return ""
    context = _build_context_blocks(hits)
    messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
    if history_messages:
        messages.extend(history_messages)
    messages.append(
        {
            "role": "user",
            "content": f"Context:\n\n{context}\n\n---\n\nQuestion: {user_query}",
        }
    )
    try:
        resp = _ollama_mod.chat(
            model=llm_model,
            messages=messages,
            stream=False,
            options=_ollama_options_for_model(llm_model),
        )
        msg = getattr(resp, "message", None) or (resp.get("message") if isinstance(resp, dict) else None)
        if isinstance(msg, dict):
            return str(msg.get("content") or "")
        return str(getattr(msg, "content", None) or "")
    except Exception as exc:
        err = str(exc).lower()
        if "not found" in err or "pull" in err:
            print(
                f"Error: model {llm_model!r} not found. Run: ollama pull {llm_model}",
                file=sys.stderr,
            )
        else:
            print(f"Error: LLM call failed: {exc}", file=sys.stderr)
        return ""


def _stream_llm_answer(
    user_query: str,
    hits: List[SearchHit],
    llm_model: str,
    system_prompt: str,
    console: Any,
    history_messages: Optional[List[Dict[str, str]]] = None,
) -> str:
    if not OLLAMA_LIB_AVAILABLE or _ollama_mod is None:
        print("Warning: ollama package not installed; skipping LLM answer.", file=sys.stderr)
        return ""
    context = _build_context_blocks(hits)
    messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
    if history_messages:
        messages.extend(history_messages)
    messages.append(
        {
            "role": "user",
            "content": f"Context:\n\n{context}\n\n---\n\nQuestion: {user_query}",
        }
    )
    try:
        stream = _ollama_mod.chat(
            model=llm_model,
            messages=messages,
            stream=True,
            options=_ollama_options_for_model(llm_model),
        )
    except Exception as exc:
        err = str(exc).lower()
        if "not found" in err or "pull" in err:
            print(
                f"Error: model {llm_model!r} not found. Run: ollama pull {llm_model}",
                file=sys.stderr,
            )
        else:
            print(f"Error: LLM call failed: {exc}", file=sys.stderr)
        return ""

    parts: List[str] = []
    try:
        if console and RICH_AVAILABLE and Live is not None and Markdown is not None:
            with Live(Markdown(""), console=console, refresh_per_second=12, transient=False) as live:
                for chunk in stream:
                    tok = _stream_chunk_text(chunk)
                    if tok:
                        parts.append(tok)
                        live.update(Markdown("".join(parts)))
        else:
            for chunk in stream:
                tok = _stream_chunk_text(chunk)
                if tok:
                    parts.append(tok)
                    print(tok, end="", flush=True)
            if parts:
                print()
    except KeyboardInterrupt:
        print("\n(generation interrupted)", file=sys.stderr)
    return "".join(parts)


class ConversationMemory:
    def __init__(self, max_turns: int = 5) -> None:
        self.max_turns = max(1, max_turns)
        self.turns: List[Dict[str, str]] = []

    def add_turn(self, raw_query: str, reformulated: str, answer_summary: str) -> None:
        self.turns.append(
            {
                "query": raw_query,
                "reformulated": reformulated,
                "answer_summary": answer_summary[:500],
            }
        )
        if len(self.turns) > self.max_turns:
            self.turns = self.turns[-self.max_turns :]

    def clear(self) -> None:
        self.turns.clear()

    def is_empty(self) -> bool:
        return not self.turns

    def recent_context_text(self, n: int = 2) -> str:
        if not self.turns:
            return ""
        lines: List[str] = []
        for t in self.turns[-n:]:
            q = t["reformulated"] or t["query"]
            lines.append(f"Q: {q}")
            if t.get("answer_summary"):
                lines.append(f"A: {t['answer_summary']}")
        return "\n".join(lines)

    def show(self) -> str:
        if not self.turns:
            return "(no conversation history)"
        lines: List[str] = []
        for i, t in enumerate(self.turns, 1):
            q = t["query"]
            r = t["reformulated"]
            extra = f"  → search: {r}" if r and r != q else ""
            lines.append(f"  {i}. {q}{extra}")
        return "\n".join(lines)

    def history_messages_for_llm(self) -> List[Dict[str, str]]:
        out: List[Dict[str, str]] = []
        for t in self.turns[-3:]:
            out.append({"role": "user", "content": t["reformulated"] or t["query"]})
            if t.get("answer_summary"):
                out.append({"role": "assistant", "content": t["answer_summary"]})
        return out


def reformulate_query(raw_query: str, memory: ConversationMemory, llm_model: str) -> str:
    if memory.is_empty():
        return raw_query
    if len(raw_query.split()) > 8:
        return raw_query
    if not OLLAMA_LIB_AVAILABLE or _ollama_mod is None:
        return raw_query
    ctx = memory.recent_context_text(2)
    prompt = (
        "Rewrite this follow-up into ONE standalone search query (under 20 words) "
        "that someone could type without prior context.\n\n"
        f"Prior turns:\n{ctx}\n\nFollow-up: {raw_query}\n\nStandalone query:"
    )
    try:
        resp = _ollama_mod.chat(
            model=llm_model,
            messages=[{"role": "user", "content": prompt}],
            stream=False,
            options={"num_predict": 80},
        )
        msg = getattr(resp, "message", None) or (
            resp.get("message") if isinstance(resp, dict) else None
        )
        text = ""
        if isinstance(msg, dict):
            text = str(msg.get("content") or "").strip()
        else:
            text = str(getattr(msg, "content", None) or "").strip()
        text = text.split("\n")[0].strip().strip('"').strip("'")
        if 3 < len(text) < 200:
            return text
    except Exception:
        pass
    return raw_query


class SessionState:
    def __init__(self, ns: argparse.Namespace) -> None:
        self.domain = ns.domain or ""
        self.repo = ns.repo or ""
        self.top_k = max(1, min(int(ns.top_k), MAX_K))
        self.search_type = ns.search_type
        self.out_format = ns.format
        self.mode = ns.mode  # semantic | concept | codebase
        self.timeout = int(ns.timeout)
        self.chat = bool(getattr(ns, "chat", False))
        cli_llm = (getattr(ns, "llm_model", None) or "").strip()
        self.llm_model = cli_llm or default_chat_llm_from_env()
        sp = (getattr(ns, "system_prompt", None) or "").strip()
        self.system_prompt_override: Optional[str] = sp if sp else None
        self.history_depth = max(1, int(getattr(ns, "history_depth", 5)))

    def apply_set(self, key: str, value: str) -> str:
        k = key.lower().strip()
        v = value.strip()
        if k == "domain":
            self.domain = v
        elif k == "k" or k == "top_k":
            try:
                self.top_k = max(1, min(int(v), MAX_K))
            except ValueError:
                return "k must be an integer"
        elif k == "type" or k == "search-type":
            allowed = {"auto", "code", "domain", "troubleshoot", "reference"}
            if v not in allowed:
                return f"type must be one of: {', '.join(sorted(allowed))}"
            self.search_type = v
        elif k == "repo":
            self.repo = v
        elif k == "format":
            if v not in ("markdown", "json", "plain"):
                return "format must be markdown, json, or plain"
            self.out_format = v
        elif k == "mode":
            if v not in ("semantic", "concept", "codebase"):
                return "mode must be semantic, concept, or codebase (use /status for DB status)"
            self.mode = v
        elif k == "timeout":
            try:
                self.timeout = max(1, int(v))
            except ValueError:
                return "timeout must be an integer"
        elif k in ("history_depth", "history-depth"):
            try:
                self.history_depth = max(1, int(v))
            except ValueError:
                return "history_depth must be an integer"
        elif k == "chat":
            if v.lower() in ("1", "true", "yes", "on"):
                self.chat = True
            elif v.lower() in ("0", "false", "no", "off"):
                self.chat = False
            else:
                return "chat must be on or off"
        else:
            return f"Unknown key: {key}"
        return f"OK: {k} = {v!r}"

    def show(self) -> str:
        return (
            f"domain={self.domain!r} repo={self.repo!r} k={self.top_k} "
            f"search_type={self.search_type!r} format={self.out_format!r} "
            f"mode={self.mode!r} timeout={self.timeout} chat={self.chat} "
            f"llm_model={self.llm_model!r} history_depth={self.history_depth}"
        )


def _setup_readline() -> None:
    if readline is None:
        return
    try:
        if HISTORY_FILE.exists():
            readline.read_history_file(str(HISTORY_FILE))
    except OSError:
        pass
    readline.set_history_length(500)


def _save_history() -> None:
    if readline is None:
        return
    try:
        readline.write_history_file(str(HISTORY_FILE))
    except OSError:
        pass


def repl_loop(
    cmap: Dict[str, Chroma],
    db_path: str,
    ns: argparse.Namespace,
    chroma_client: chromadb.PersistentClient,
    embedder: OllamaEmbeddings,
) -> int:
    st = SessionState(ns)
    memory = ConversationMemory(st.history_depth)
    log = logging.getLogger("query")
    _setup_readline()
    print("Interactive RAG query. Type /help for commands, Ctrl+D to exit.")
    print(st.show())
    while True:
        try:
            line = input("rag> ").strip()
        except EOFError:
            print()
            _save_history()
            return EXIT_OK
        except KeyboardInterrupt:
            print("\n(Interrupted — empty line or /quit to exit)")
            continue
        if not line:
            continue
        if line in ("/quit", "/exit", "exit", "quit"):
            _save_history()
            return EXIT_OK
        if line == "/help":
            print(
                "Commands: /set, /show, /help, /status, /history, /clear, /quit\n"
                "  /set <key> <value>\n"
                "Keys: domain, k, type, repo, format, mode, timeout, chat, history_depth\n"
                "Anything else is treated as a search query."
            )
            continue
        if line == "/show":
            print(st.show())
            continue
        if line == "/status":
            print(run_status(db_path))
            continue
        if line == "/history":
            print(memory.show())
            continue
        if line == "/clear":
            memory.clear()
            print("Conversation memory cleared.")
            continue
        if line.startswith("/set "):
            rest = line[5:].strip()
            parts = rest.split(None, 1)
            if len(parts) < 2:
                print("Usage: /set <key> <value>")
                continue
            msg = st.apply_set(parts[0], parts[1])
            print(msg)
            key0 = parts[0].lower().strip()
            if msg.startswith("OK") and key0 in ("history_depth", "history-depth"):
                memory.max_turns = st.history_depth
            continue

        raw_query = line
        search_query = raw_query
        if st.chat and st.mode != "concept" and not memory.is_empty():
            search_query = reformulate_query(raw_query, memory, st.llm_model)
            if search_query != raw_query:
                print(f'(searching for: "{search_query}")')

        rich_ui = RICH_AVAILABLE and st.out_format == "markdown"
        console = _make_console(no_color=bool(ns.no_color)) if rich_ui else None

        effective_type = "code" if st.mode == "codebase" else st.search_type
        try:
            with _status_spinner(console, "Searching..."):
                if st.mode == "concept":
                    hits = run_with_timeout(
                        st.timeout,
                        concept_search_hits,
                        search_query,
                        st.domain,
                        cmap,
                    )
                else:
                    hits = run_with_timeout(
                        st.timeout,
                        _sync_multi_search_with_dependency_hop,
                        search_query,
                        st.top_k,
                        effective_type,
                        st.domain,
                        st.repo,
                        cmap,
                        db_path,
                    )
        except (TimeoutError, ValueError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            continue
        except Exception as exc:
            log.exception("query failed")
            print(f"Error: {exc}", file=sys.stderr)
            continue
        if not hits:
            if st.mode == "concept":
                print(f"No chunks tagged with concept '{search_query}'.")
            else:
                print("No matching chunks found.")
            continue

        hist_msgs = memory.history_messages_for_llm() if st.chat else None
        eff_sp = _effective_system_prompt(
            hits, effective_type, st.system_prompt_override, st.domain
        )

        if st.chat:
            llm_tag = _check_model_available(st.llm_model)
            if st.mode == "concept":
                if st.out_format == "json":
                    ans = _collect_llm_answer(
                        raw_query,
                        hits,
                        llm_tag,
                        eff_sp,
                        hist_msgs,
                    )
                    print(format_json_output(raw_query, hits, "concept", answer=ans))
                elif st.out_format == "markdown":
                    ans = _stream_llm_answer(
                        raw_query,
                        hits,
                        llm_tag,
                        eff_sp,
                        console,
                        hist_msgs,
                    )
                else:
                    ans = _stream_llm_answer(
                        raw_query,
                        hits,
                        llm_tag,
                        eff_sp,
                        None,
                        hist_msgs,
                    )
                memory.add_turn(raw_query, search_query, ans or "(no answer)")
                continue

            if st.out_format == "json":
                ans = _collect_llm_answer(
                    raw_query,
                    hits,
                    llm_tag,
                    eff_sp,
                    hist_msgs,
                )
                print(format_json_output(raw_query, hits, st.mode, answer=ans))
            elif st.out_format == "markdown":
                ans = _stream_llm_answer(
                    raw_query,
                    hits,
                    llm_tag,
                    eff_sp,
                    console,
                    hist_msgs,
                )
            else:
                ans = _stream_llm_answer(
                    raw_query,
                    hits,
                    llm_tag,
                    eff_sp,
                    None,
                    hist_msgs,
                )
            memory.add_turn(raw_query, search_query, ans or "(no answer)")
            continue

        if st.mode == "concept":
            if st.out_format == "json":
                print(format_json_output(raw_query, hits, "concept"))
            elif st.out_format == "markdown":
                _print_rich(console, format_concept_markdown(hits, raw_query))
            else:
                print(format_plain(hits))
        else:
            if st.out_format == "json":
                print(format_json_output(raw_query, hits, st.mode))
            elif st.out_format == "markdown":
                _print_rich(console, format_markdown(hits, raw_query))
            else:
                print(format_plain(hits))
    return EXIT_OK


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Query Universal Domain RAG (Chroma + Ollama).")
    p.add_argument("-q", "--query", default="", help="Search text (concept id in concept mode)")
    p.add_argument(
        "-m",
        "--mode",
        choices=("semantic", "concept", "codebase", "status"),
        default="semantic",
        help="Search mode (default: semantic)",
    )
    p.add_argument(
        "-t",
        "--search-type",
        choices=("auto", "code", "domain", "troubleshoot", "reference"),
        default="auto",
        help="Collection routing for semantic/codebase (default: auto)",
    )
    p.add_argument("-d", "--domain", default="", help="Filter collections by name substring")
    p.add_argument("-r", "--repo", default="", help="Filter by repository metadata")
    p.add_argument("-k", "--top-k", type=int, default=TOP_K_DEFAULT, help=f"Max results (1–{MAX_K})")
    p.add_argument(
        "-f",
        "--format",
        dest="format",
        choices=("markdown", "json", "plain"),
        default="markdown",
        help="Output format",
    )
    p.add_argument("-o", "--output", default="", help="Write output to file instead of stdout")
    p.add_argument(
        "-c",
        "--chat",
        action="store_true",
        help="After retrieval, generate an answer with the LLM (Ollama chat)",
    )
    p.add_argument(
        "--llm-model",
        default="",
        help="Ollama chat model for --chat (default: gemma3:27b; env RAG_LLM_MODEL overrides when flag omitted)",
    )
    p.add_argument(
        "--system-prompt",
        default="",
        help="Override default RAG system prompt when using --chat",
    )
    p.add_argument(
        "--history-depth",
        type=int,
        default=5,
        help="REPL: max conversation turns to remember with --chat (default: 5)",
    )
    p.add_argument("--no-color", action="store_true", help="Disable color (rich/ANSI)")
    p.add_argument(
        "--db-path",
        default=os.environ.get("DB_PATH", "").strip()
        or str(Path(__file__).resolve().parent / "Studio-Portable-RAG" / "VectorDB"),
        help="Chroma persist directory",
    )
    p.add_argument("--model", default="", help="Embedding model (default: auto-detect)")
    p.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Per-query timeout (seconds)")
    p.add_argument("-i", "--interactive", action="store_true", help="Interactive REPL")
    p.add_argument("-v", "--verbose", action="store_true", help="Verbose logging on stderr")
    p.add_argument("--quiet", action="store_true", help="Suppress banners")
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    ns = parse_args(argv)
    log = logging.getLogger("query")
    logging.basicConfig(
        level=logging.DEBUG if ns.verbose else logging.WARNING,
        format="%(levelname)s %(message)s",
        stream=sys.stderr,
    )

    db_path = str(Path(ns.db_path).resolve())
    if not Path(db_path).is_dir():
        if not ns.quiet:
            print(f"Error: DB path is not a directory: {db_path}", file=sys.stderr)
        return EXIT_INFRA

    need_query = not ns.interactive and ns.mode != "status"
    if need_query and not (ns.query or "").strip():
        if not ns.quiet:
            print("Error: --query is required unless --interactive or --mode status", file=sys.stderr)
        return EXIT_ARG

    if ns.mode == "status":
        text = run_status(db_path)
        if ns.output:
            Path(ns.output).write_text(text, encoding="utf-8")
        else:
            print(text)
        return EXIT_OK

    if not check_ollama():
        if not ns.quiet:
            print(
                "Error: Ollama not reachable at http://127.0.0.1:11434/api/tags. "
                "Start Ollama or use query.sh.",
                file=sys.stderr,
            )
        return EXIT_INFRA

    model = ns.model.strip() or detect_embedding_model(db_path)
    if not ns.quiet:
        print(f"DB: {db_path}\nModel: {model}", file=sys.stderr)

    try:
        chroma_client, embedder, cmap = connect_chroma_with_retry(db_path, model)
    except Exception as exc:
        if not ns.quiet:
            print(f"Error: {exc}", file=sys.stderr)
        return EXIT_INFRA

    if not cmap:
        if not ns.quiet:
            print("Error: no Chroma collections in DB.", file=sys.stderr)
        return EXIT_INFRA

    if ns.interactive:
        return repl_loop(cmap, db_path, ns, chroma_client, embedder)

    effective_type = "code" if ns.mode == "codebase" else ns.search_type
    try:
        k = max(1, min(int(ns.top_k), MAX_K))
    except (TypeError, ValueError):
        k = TOP_K_DEFAULT

    q = ns.query.strip()
    spin_console = _make_console(no_color=bool(ns.no_color)) if (
        RICH_AVAILABLE and ns.format == "markdown"
    ) else None
    display_console = _make_console(no_color=bool(ns.no_color)) if (
        RICH_AVAILABLE and ns.format == "markdown" and not ns.output
    ) else None

    try:
        with _status_spinner(spin_console, "Searching..."):
            if ns.mode == "concept":
                hits = run_with_timeout(
                    int(ns.timeout),
                    concept_search_hits,
                    q,
                    ns.domain,
                    cmap,
                )
            else:
                hits = run_with_timeout(
                    int(ns.timeout),
                    _sync_multi_search_with_dependency_hop,
                    q,
                    k,
                    effective_type,
                    ns.domain,
                    ns.repo,
                    cmap,
                    db_path,
                )
    except TimeoutError as exc:
        if not ns.quiet:
            print(f"Error: {exc}", file=sys.stderr)
        return EXIT_INFRA
    except Exception as exc:
        log.exception("search failed")
        if not ns.quiet:
            print(f"Error: {exc}", file=sys.stderr)
        return EXIT_INFRA

    if not hits:
        msg = "No matching chunks found."
        if ns.output:
            Path(ns.output).write_text(msg + "\n", encoding="utf-8")
        elif not ns.quiet:
            print(msg)
        return EXIT_NO_RESULTS

    llm_model = (ns.llm_model or "").strip() or default_chat_llm_from_env()
    sp_override = (ns.system_prompt or "").strip() or None
    system_prompt = _effective_system_prompt(hits, effective_type, sp_override, ns.domain)

    if ns.chat:
        llm_tag = _check_model_available(llm_model)
        if ns.mode == "concept":
            mode_label = "concept"
        else:
            mode_label = ns.mode
        if ns.format == "json":
            ans = _collect_llm_answer(q, hits, llm_tag, system_prompt, None)
            text = format_json_output(q, hits, mode_label, answer=ans)
            if ns.output:
                Path(ns.output).write_text(text, encoding="utf-8")
            else:
                print(text)
            return EXIT_OK
        if ns.format == "plain":
            if ns.output:
                ans = _collect_llm_answer(q, hits, llm_tag, system_prompt, None)
                Path(ns.output).write_text(ans + ("\n" if ans and not ans.endswith("\n") else ""), encoding="utf-8")
            else:
                _stream_llm_answer(q, hits, llm_tag, system_prompt, None, None)
            return EXIT_OK
        # markdown
        if ns.output:
            ans = _collect_llm_answer(q, hits, llm_tag, system_prompt, None)
            Path(ns.output).write_text(ans + ("\n" if ans and not ans.endswith("\n") else ""), encoding="utf-8")
        else:
            _stream_llm_answer(q, hits, llm_tag, system_prompt, display_console, None)
        return EXIT_OK

    if ns.mode == "concept":
        text = (
            format_json_output(q, hits, "concept")
            if ns.format == "json"
            else format_concept_markdown(hits, q)
            if ns.format == "markdown"
            else format_plain(hits)
        )
    else:
        text = (
            format_json_output(q, hits, ns.mode)
            if ns.format == "json"
            else format_markdown(hits, q)
            if ns.format == "markdown"
            else format_plain(hits)
        )

    if ns.output:
        Path(ns.output).write_text(text, encoding="utf-8")
    elif ns.format == "markdown" and display_console:
        _print_rich(display_console, text)
    else:
        print(text)
    return EXIT_OK


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        sys.exit(130)
