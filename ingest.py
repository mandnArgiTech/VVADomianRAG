#!/usr/bin/env python3
"""
Universal domain RAG ingestion: multi-mode CLI, multi-collection Chroma,
deterministic IDs + upsert, checkpointing, and pluggable chunk strategies.
"""
from __future__ import annotations

import argparse
import ast
import asyncio
import csv
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from dataclasses import dataclass
import hashlib
import uuid
import json
import logging
import os
import queue
import re
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, FrozenSet, Iterable, List, Optional, Set, Tuple

from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import Language, RecursiveCharacterTextSplitter
from tqdm import tqdm

try:
    from tqdm.asyncio import tqdm as tqdm_asyncio
except ImportError:  # pragma: no cover
    tqdm_asyncio = None

try:
    import chromadb
except ImportError as exc:  # pragma: no cover
    raise SystemExit("chromadb is required") from exc

from util.chroma_client import safe_collection_count as _safe_count_util

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None  # type: ignore

try:
    import aiohttp  # type: ignore
except ImportError:  # pragma: no cover
    aiohttp = None  # type: ignore

try:
    import pathspec  # type: ignore
except ImportError:  # pragma: no cover
    pathspec = None  # type: ignore

try:
    from sanitizer import sanitize as sanitize_pii
except ImportError:  # pragma: no cover
    sanitize_pii = None  # type: ignore

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover
    BeautifulSoup = None  # type: ignore

from ingest_kit.config import DEFAULT_RFC_TOKEN_LIMIT, MIB_MODULE_CONCEPTS, MODEL_TOKEN_LIMITS
from ingest_kit.concepts import format_concepts_field, iter_concept_ids
from ingest_kit.treesitter import TreeSitterFallbackDisallowedError, _ts_parser_for

from ingest_kit.chunking.chapter_domain import _chapter_meta_from_filename, _domain_doc_content_type
from ingest_kit.chunking.code_pipeline import (
    _REGEX_CODE_PATTERNS,
    _device_family_for_path,
    _extract_py_calls,
    _filter_tiny_code_chunks,
    _format_calls_metadata,
    _js_ts_lang,
    _merge_small_regex_chunks,
    ast_chunk_python,
    chunk_scheme,
    generic_split,
    language_split,
    regex_code_split,
    regex_spice_split,
    sentence_window,
    _ts_extract_chunks,
    _ts_extract_chunks_or_language_split_c_cpp,
    _ts_extract_chunks_or_language_split_java,
)
from ingest_kit.chunking.community_wiki import chunk_community, chunk_wiki_page, parse_frontmatter
from ingest_kit.chunking.markdown import chunk_markdown_domain
from ingest_kit.chunking.mib import chunk_mib
from ingest_kit.chunking.paragraphs import (
    _apply_chunk_min_merge,
    _merge_small_chunks,
    _split_paragraphs,
    _top_section,
)
from ingest_kit.chunking.releases import chunk_release_notes
from ingest_kit.chunking.rfc import chunk_rfc
from ingest_kit.chunking.rfc_preprocess import (
    _depaginate_rfc,
    _diagram_vault_sort_key,
    _is_rfc_file,
    _rfc_line_is_diagram,
    _shield_diagrams,
    _sliding_window_chunks,
    _unshield_diagrams,
)
from ingest_kit.chunking.shared import (
    _extract_release_date_near_version,
    _extract_source_c_files,
    _file_preamble_block_comment,
    _mask_markdown_fences_and_tables,
    _protect_math_blocks,
    _restore_math_blocks,
    _ts_comment_prefix,
    _unmask_markdown_with_meta,
)
from ingest_kit.chunking.sizing import _estimate_tokens, _get_rfc_token_limit, _md_char_targets
from ingest_kit.chunking.tickets import chunk_customer_ticket, chunk_rally_ticket
from ingest_kit.embedding.http_async import (
    _async_http_embed_batch,
    embed_with_retry_http_async,
    run_async_embedding_batches,
)
from ingest_kit.cli import (
    _NGSPICE_GITIGNORE_ENTRIES,
    build_arg_parser,
    main,
    write_ngspice_gitignore,
)
from ingest_kit.pipeline.orchestrator import ingest_run


def strip_html(text: str) -> str:
    """Strip HTML for ticket/wiki helpers (defined here so tests can patch ``BeautifulSoup``)."""
    if BeautifulSoup is not None:
        return BeautifulSoup(text, "html.parser").get_text("\n")
    return re.sub(r"<[^>]+>", " ", text)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

INGESTION_VERSION = "2.0"
MAX_RETRIES = 5
EMBED_BACKOFF_SEC = 5
SCRIPT_DIR = Path(__file__).resolve().parent


def _default_vector_db_dir() -> str:
    """Default Chroma dir: next to ingest in the portable bundle, else repo ``Studio-Portable-RAG/VectorDB``."""
    p = SCRIPT_DIR
    if p.name == "Studio-Portable-RAG":
        return str((p / "VectorDB").resolve())
    return str((p / "Studio-Portable-RAG" / "VectorDB").resolve())


METADATA_KEYS = [
    "source",
    "source_type",
    "domain",
    "repository",
    "relative_path",
    "extension",
    "file_size_kb",
    "last_modified",
    "chunk_strategy",
    "chunk_type",
    "chunk_name",
    "chunk_index",
    "section",
    "subsection",
    "content_type",
    "concepts",
    "ingestion_date",
    "ingestion_version",
    "rfc_number",
    "rfc_title",
    "section_number",
    "section_title",
    "contains_diagram",
    "diagram_type",
    "rally_id",
    "ticket_id",
    "mib_module",
    "oid_path",
    "page_title",
    "space",
    "labels",
    "author",
    "parent_page",
    "page_url",
    "version",
    "release_date",
    "section_category",
    "artifact_type",
    "state",
    "priority",
    "iteration",
    "release",
    "created_date",
    "closed_date",
    "tags",
    "customer_type",
    "product_version",
    "related_rally",
    "syntax",
    "max_access",
    "status",
    "object_type",
    "source_platform",
    "source_url",
    "is_resolved",
    "has_resolution",
    "has_workaround",
    "severity",
    "quality_score",
    "doc_title",
    "object_name",
    "context_window",
    "dependencies",
    "device_family",
    "structural_importance",
    "calls",
    "llm_summary",
    "llm_tags",
    "llm_relations",
    "llm_physics_model",
    "source_c_files",
    "chapter_number",
]

CONTENT_TYPE_SIGNALS = {
    "edge_case": [
        "edge case",
        "workaround",
        "gotcha",
        "corner case",
        "fails when",
        "breaks when",
        "known issue",
        "known bug",
        "unexpected",
        "pitfall",
    ],
    "algorithm": [
        "algorithm",
        "how it works",
        "process",
        "steps",
        "flow",
        "procedure",
        "computes",
        "iterates",
        "pseudocode",
    ],
    "rationale": [
        "the reason why",
        "that's why we",
        "rationale",
        "design decision",
        "trade-off",
        "tradeoff",
        "motivation for",
        "we chose",
        "was chosen because",
        "instead of",
        "the thinking behind",
        "decided to",
    ],
    "glossary": [
        "glossary",
        "definition",
        "terminology",
        "is defined as",
        "refers to",
    ],
    "interaction": [
        "depends on",
        "feeds into",
        "consumed by",
        "upstream",
        "downstream",
        "triggered by",
        "interface",
        "contract",
    ],
    "constraint": [
        "assumption",
        "constraint",
        "limitation",
        "prerequisite",
        "must be",
        "cannot",
        "restricted",
        "only works",
    ],
    "bug_report": [
        "bug",
        "defect",
        "regression",
        "crash",
        "root cause",
        "steps to reproduce",
        "reproduc",
    ],
    "workaround": ["workaround", "temporary fix", "mitigation", "until fixed"],
    "howto": [
        "how to",
        "tutorial",
        "step by step",
        "getting started",
        "example",
    ],
    "api": [
        "api",
        "function signature",
        "parameters",
        "returns",
        "class reference",
    ],
}

# Target max tokens per chunk for RFC splitting (char budget ~= tokens * 4).

STRATEGY_SIZE_LIMIT_MB = {
    "code": 5,
    "domain_doc": 10,
    "theory": 20,
    "config": 2,
    "mib": 5,
    "ticket": 5,
    "rfc": 2,
    "release_notes": 10,
    "community": 5,
    "wiki": 10,
    "default": 5,
}


# Config / data files (plan: 2 MB cap when ingested as code)
CONFIG_EXTS = {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".properties", ".xml"}

# Code-mode traversal: skip VCS, deps, build outputs, and common binaries
IGNORED_DIRS = {
    ".git",
    ".svn",
    ".hg",
    "node_modules",
    "build",
    "dist",
    "target",
    "__pycache__",
    "bin",
    "obj",
    "vendor",
    ".idea",
    ".vs",
    ".vscode",
    ".venv",
    "venv",
    ".tox",
    ".eggs",
    ".mypy_cache",
    ".pytest_cache",
    "CMakeFiles",
    "Debug",
    "Release",
    "x64",
    "x86",
}

IGNORED_EXTS = {
    ".exe",
    ".dll",
    ".so",
    ".o",
    ".a",
    ".lib",
    ".class",
    ".jar",
    ".zip",
    ".tar",
    ".gz",
    ".7z",
    ".rar",
    ".bz2",
    ".xz",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".ico",
    ".webp",
    ".bmp",
    ".pdf",
    ".bin",
    ".wasm",
    ".lock",
    ".pyc",
    ".pyo",
    ".pdb",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".map",
    ".mp3",
    ".mp4",
    ".avi",
    ".mov",
    ".wmv",
    ".db",
    ".sqlite",
    ".sqlite3",
}

shutdown_event = threading.Event()
_embed_lock = threading.Lock()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logger = logging.getLogger("ingest")


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    # asyncio logs "Using selector: EpollSelector" at DEBUG when --verbose; it looks like a hang
    # in GUI/SSE logs and is almost never useful for ingest operators.
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    if not verbose:
        for noisy in ("aiohttp", "aiohttp.client", "aiohttp.connector", "chromadb", "httpx"):
            logging.getLogger(noisy).setLevel(logging.WARNING)


def _tqdm_ingest(iterable: Iterable[Any], *, desc: str, unit: str, **kwargs: Any) -> tqdm:
    """tqdm tuned for piped stdout (GUI SSE): frequent enough that idle watchdogs see progress."""
    opts: Dict[str, Any] = {"desc": desc, "unit": unit}
    if not sys.stdout.isatty():
        # Default 0.5s: long per-file steps (e.g. LLM enrich per chunk) otherwise produce no lines for
        # tens of seconds and the GUI repeats "still running". Override with INGEST_TQDM_MININTERVAL.
        opts["mininterval"] = float(os.environ.get("INGEST_TQDM_MININTERVAL", "0.5"))
        opts["maxinterval"] = 15.0
    opts.update(kwargs)
    return tqdm(iterable, **opts)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_chunk_id(source: str, chunk_index: int, content: str) -> str:
    h = hashlib.sha256(f"{source}::{chunk_index}::{content}".encode("utf-8", errors="replace"))
    return h.hexdigest()[:20]


def resolve_collection(mode: str, domain: str, override: Optional[str]) -> str:
    if override:
        return override
    routes = {
        "code": "{domain}_code",
        "domain": "{domain}_domain",
        "rfc": "rfc",
        "rally": "{domain}_internal",
        "customer": "{domain}_customer",
        "mib": "{domain}_mib",
        "wiki": "{domain}_wiki",
        "release-notes": "{domain}_releases",
        "theory": "theory",
        "community": "community",
    }
    key = routes.get(mode, "{domain}_misc")
    return key.format(domain=domain)


def empty_metadata() -> Dict[str, str]:
    return {k: "" for k in METADATA_KEYS}


def finalize_metadata(meta: Dict[str, Any]) -> Dict[str, str]:
    out = empty_metadata()
    for k in METADATA_KEYS:
        if k in meta and meta[k] is not None and meta[k] != "":
            out[k] = str(meta[k])
    return out


def detect_content_type(text: str) -> str:
    tl = text.lower()
    scores = {
        ct: sum(1 for s in sigs if s in tl) for ct, sigs in CONTENT_TYPE_SIGNALS.items()
    }
    scores = {k: v for k, v in scores.items() if v > 0}
    return max(scores, key=scores.get) if scores else "general"


def load_concept_registry(path: Path) -> Dict[str, Dict[str, str]]:
    if path.exists():
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                return {k: {str(a): str(b) for a, b in v.items()} for k, v in data.items() if isinstance(v, dict)}
        except Exception as exc:  # pragma: no cover
            logger.warning("Could not load concept registry: %s", exc)  # pragma: no cover
    # minimal defaults if missing
    return {
        "nms": {"vlan": "vlan", "snmp": "snmp_polling"},
        "occt": {"fillet": "fillet"},
        "spice": {"transient": "transient_analysis"},
        "kicad": {"footprint": "footprint"},
        "geda": {"netlist": "netlist"},
        "general": {},
    }


def extract_concepts(text: str, domain: str, registry: Dict[str, Dict[str, str]]) -> str:
    dom = domain if domain in registry else "general"
    table = registry.get(dom, {})
    if not table:
        return ""
    tl = text.lower()
    found = set()
    for keyword in sorted(table.keys(), key=len, reverse=True):
        if re.search(rf"\b{re.escape(keyword.lower())}\b", tl):
            found.add(table[keyword])
    return format_concepts_field(found) if found else ""






def read_file_bytes(path: Path) -> Tuple[Optional[str], str]:
    raw = path.read_bytes()
    for enc in ("utf-8", "latin-1", "cp1252", "iso-8859-1"):
        try:
            return raw.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return None, "binary"  # pragma: no cover


def file_md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(65536), b""):
            h.update(block)
    return h.hexdigest()




def _safe_count(coll) -> int:
    return _safe_count_util(coll)


def parse_rally_filter(filter_str: Optional[str]) -> Dict[str, Any]:
    """Parse --rally-filter e.g. 'severity=1,2,3 state=Closed'."""
    if not filter_str or not str(filter_str).strip():
        return {}
    rules: Dict[str, Any] = {}
    for part in re.split(r"\s+", str(filter_str).strip()):
        if "=" not in part:
            continue
        k, v = part.split("=", 1)
        key = k.strip().lower()
        val = v.strip()
        if key == "severity":
            rules["severity"] = {x.strip() for x in val.split(",") if x.strip()}
        elif key == "state":
            rules["state"] = val
        elif key == "priority":
            rules["priority"] = val  # pragma: no cover
        else:
            rules[key] = val
    return rules


def rally_matches_user_filter(obj: Dict[str, Any], rules: Dict[str, Any]) -> bool:
    if not rules:
        return True
    if "severity" in rules:
        sev = str(obj.get("Severity") or obj.get("severity") or "").strip()
        if sev and sev not in rules["severity"]:
            return False
    if "state" in rules:
        st = str(obj.get("State") or obj.get("state") or "")
        want = str(rules["state"])
        if want and st.lower() != want.lower():
            return False
    if "priority" in rules:
        pr = str(obj.get("Priority") or obj.get("priority") or "")  # pragma: no cover
        want = str(rules["priority"])  # pragma: no cover
        if want and want.lower() not in pr.lower():  # pragma: no cover
            return False  # pragma: no cover
    return True










def _format_dependencies_field(modules: Iterable[str]) -> str:
    """Comma-separated sorted list for human-readable metadata and Chroma token search."""
    unique = sorted({m.strip() for m in modules if m and str(m).strip()})
    if not unique:
        return ""
    return ", ".join(unique)


# Pre-pass scans only a prefix of each file for import/include lines (performance).
_STRUCTURAL_REFSCAN_BYTES = 8192


def _normalize_refcount_stem(raw: str) -> str:
    """Map dependency token to a filename stem for structural_importance keys."""
    s = (raw or "").strip().replace("\\", "/")
    if not s:
        return ""
    return Path(s).stem


def _extract_dependency_stems(content: str, ext: str) -> List[str]:
    """Return raw dependency tokens (includes, modules) found in *content* (same logic as extract_dependencies)."""
    ext_l = ext.lower()
    mods: List[str] = []

    if ext_l == ".py":
        try:
            tree = ast.parse(content)
        except SyntaxError:
            for m in re.finditer(
                r"(?m)^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.,\s]+))\s*",
                content,
            ):
                g1, g2 = m.group(1), m.group(2)
                if g1:
                    mods.append(g1.split(".")[0])
                if g2:
                    for part in g2.replace(",", " ").split():
                        if part and part not in ("import", "as"):
                            mods.append(part.split(".")[0])
        else:

            class V(ast.NodeVisitor):
                def visit_Import(self, node: ast.Import) -> None:
                    for alias in node.names:
                        mods.append((alias.name or "").split(".")[0])

                def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
                    if node.module:
                        mods.append(node.module.split(".")[0])
                    for alias in node.names:
                        if alias.name != "*":
                            mods.append(alias.name)

            V().visit(tree)

    elif ext_l in (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"):
        for m in re.finditer(
            r"""import\s+(?:[\w*{}\s,]+\s+from\s+)?['"]([^'"]+)['"]|"""
            r"""require\s*\(\s*['"]([^'"]+)['"]\s*\)|"""
            r"""import\s*\(\s*['"]([^'"]+)['"]\s*\)""",
            content,
        ):
            for g in m.groups():
                if g:
                    mods.append(g.strip().split("/")[-1].split(".")[0])

    elif ext_l in (".c", ".h", ".cpp", ".cxx", ".cc", ".hpp", ".hxx"):
        for m in re.finditer(r'#\s*include\s+([<"])([^>"]+)([>"])', content):
            mods.append(m.group(2).strip())

    elif ext_l == ".java":
        for m in re.finditer(r"(?m)^\s*import\s+([\w.]+)\s*;", content):
            mods.append(m.group(1))

    elif ext_l == ".go":
        for m in re.finditer(r'import\s+(?:\(\s*([^)]+)\s*\)|"([^"]+)")', content, re.DOTALL):
            block = m.group(1) or m.group(2) or ""
            for q in re.findall(r'"([^"]+)"', block):
                mods.append(q)
        for m in re.finditer(r'import\s+"([^"]+)"', content):
            mods.append(m.group(1))

    elif ext_l == ".rs":
        for m in re.finditer(r"(?m)^\s*(?:pub\s+)?use\s+([^;]+);", content):
            for seg in m.group(1).split(","):
                seg = seg.split("::")[0].strip()
                if seg and seg not in ("self", "super", "crate"):
                    mods.append(seg)
        for m in re.finditer(r"(?m)^\s*(?:pub\s+)?mod\s+(\w+)\s*;", content):
            mods.append(m.group(1))

    return mods


def extract_dependencies(content: str, ext: str) -> str:
    """Extract import-like symbols for metadata (comma-separated)."""
    return _format_dependencies_field(_extract_dependency_stems(content, ext))


def build_file_ref_counts_for_code_ingest(files_to_process: List[Tuple[Path, Dict[str, Any]]]) -> Dict[str, int]:
    """Count how many distinct source files reference each normalized stem (Story A pre-pass)."""
    file_ref_counts: Dict[str, int] = {}
    for path, extra in files_to_process:
        if extra.get("virtual") or not path.is_file():
            continue
        try:
            raw = path.read_bytes()[:_STRUCTURAL_REFSCAN_BYTES]
            text_pre = raw.decode("utf-8", errors="replace")
        except OSError:
            continue
        stems_raw = _extract_dependency_stems(text_pre, path.suffix.lower())
        seen_in_file: set = set()
        for stem in stems_raw:
            clean = _normalize_refcount_stem(stem)
            if clean:
                seen_in_file.add(clean)
        for clean in seen_in_file:
            file_ref_counts[clean] = file_ref_counts.get(clean, 0) + 1
    return file_ref_counts




def _is_ngspice_manual_doc_path(path: Path) -> bool:
    """True for .md/.txt/.rst under a path segment named docs (e.g. .../docs/ or .../Spice64/docs/)."""
    if path.suffix.lower() not in (".md", ".txt", ".rst"):
        return False
    return any(p.casefold() == "docs" for p in path.parts)


def choose_strategy_for_path(
    path: Path,
    source_type: str,
    mib_keep_deprecated: bool = False,
    embed_model: Optional[str] = None,
    allow_language_split_fallback: bool = False,
) -> Tuple[str, Callable[..., List[Tuple[str, Dict[str, str]]]], int, Optional[str]]:
    ext = path.suffix.lower()
    em = (embed_model or os.environ.get("EMBEDDING_MODEL", "nomic-embed-text")).strip()
    code_limit = STRATEGY_SIZE_LIMIT_MB["config"] if ext in CONFIG_EXTS else STRATEGY_SIZE_LIMIT_MB["code"]
    doc_lim = STRATEGY_SIZE_LIMIT_MB["domain_doc"]
    if source_type == "code":
        if _is_ngspice_manual_doc_path(path):
            return (
                "code",
                lambda p, c, _em=em: chunk_markdown_domain(c, str(p), embed_model=_em),
                doc_lim,
                "ngspice_manual",
            )
        if ext == ".py":
            return "code", lambda p, c: ast_chunk_python(p, c), code_limit, None
        if ext in (".c", ".h", ".inc", ".def", ".mac"):
            _af = allow_language_split_fallback
            return (
                "code",
                lambda p, c, _af=_af: _ts_extract_chunks_or_language_split_c_cpp(
                    p, c, "c", allow_language_split_fallback=_af
                ),
                code_limit,
                None,
            )
        if ext in (".cpp", ".cxx", ".cc", ".hpp", ".hxx"):
            _af = allow_language_split_fallback
            return (
                "code",
                lambda p, c, _af=_af: _ts_extract_chunks_or_language_split_c_cpp(
                    p, c, "cpp", allow_language_split_fallback=_af
                ),
                code_limit,
                None,
            )
        if ext == ".java":
            _af = allow_language_split_fallback
            return (
                "code",
                lambda p, c, _af=_af: _ts_extract_chunks_or_language_split_java(
                    p, c, allow_language_split_fallback=_af
                ),
                code_limit,
                None,
            )
        if ext == ".scm":
            return "code", lambda p, c: chunk_scheme(c, p), code_limit, None
        if ext in (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"):
            lg = _js_ts_lang(ext)
            return "code", lambda p, c, lg=lg: language_split(p, c, lg), code_limit, None
        if ext in (".md", ".txt"):
            return "code", lambda p, c: sentence_window(c, p), code_limit, None  # pragma: no cover
        if ext in (".cir", ".net", ".sp", ".mod", ".lib"):
            return "code", lambda p, c: regex_spice_split(c, p), code_limit, None
        return "code", lambda p, c: regex_code_split(c, p, ext), code_limit, None
    if source_type in ("domain_doc", "theory"):
        lim = STRATEGY_SIZE_LIMIT_MB["theory" if source_type == "theory" else "domain_doc"]
        if ext in (".md", ".txt", ".rst"):
            return (
                source_type,
                lambda p, c, _em=em: chunk_markdown_domain(c, str(p), embed_model=_em),
                lim,
                None,
            )
        return source_type, lambda p, c: generic_split(c, p, 2000), lim, None  # pragma: no cover
    if source_type == "rfc":
        return (
            "rfc",
            lambda p, c, _em=em: chunk_rfc(c, str(p), embed_model=_em),
            STRATEGY_SIZE_LIMIT_MB["rfc"],
            None,
        )
    if source_type == "mib":
        sk = not mib_keep_deprecated
        return (
            "mib",
            lambda p, c, _sk=sk: chunk_mib(c, p, skip_deprecated=_sk),
            STRATEGY_SIZE_LIMIT_MB["mib"],
            None,
        )
    if source_type == "release_notes":
        return (
            "release_notes",
            lambda p, c: chunk_release_notes(c, str(p)),
            STRATEGY_SIZE_LIMIT_MB["release_notes"],
            None,
        )
    if source_type == "community":
        return (
            "community",
            lambda p, c: chunk_community(c, str(p), {}),
            STRATEGY_SIZE_LIMIT_MB["community"],
            None,
        )
    if source_type == "wiki":
        return (
            "wiki",
            lambda p, c: chunk_wiki_page(c, str(p), {}),
            STRATEGY_SIZE_LIMIT_MB["wiki"],
            None,
        )
    return "default", lambda p, c: generic_split(c, p, 2000), STRATEGY_SIZE_LIMIT_MB["default"], None


RALLY_BASE = "https://rally1.rallydev.com/slm/webservice/v2.0"
WRITER_STOP = object()


def fetch_rally_artifacts(project_name: str, artifact_type: str = "defect", page_size: int = 200):
    if requests is None:
        raise RuntimeError("requests not installed; pip install requests")
    key = os.environ.get("RALLY_API_KEY", "").strip()
    if not key:
        raise RuntimeError("RALLY_API_KEY not set")
    headers = {"ZSESSIONID": key}
    url = f"{RALLY_BASE}/{artifact_type}"
    params = {
        "query": f'(Project.Name = "{project_name}")',
        "fetch": (
            "FormattedID,Name,Description,Notes,Discussion,Resolution,State,Priority,Severity,"
            "Tags,CreationDate,ClosedDate,Iteration,Release"
        ),
        "pagesize": page_size,
        "start": 1,
        "order": "CreationDate desc",
    }
    all_results: List[dict] = []
    while True:
        r = requests.get(url, headers=headers, params=params, timeout=120)
        r.raise_for_status()
        data = r.json().get("QueryResult") or {}
        batch = data.get("Results") or []
        all_results.extend(batch)
        total = data.get("TotalResultCount") or len(all_results)
        if len(all_results) >= total or not batch:
            break
        params["start"] = int(params["start"]) + page_size
    return all_results


def _fetch_confluence_pages_v2(
    base: str, headers: Dict[str, str], space_key: str, label: str
) -> Optional[List[Dict[str, Any]]]:
    """Try Confluence REST API v2; return None to fall back to v1."""
    try:
        sp_url = f"{base}/wiki/api/v2/spaces"
        r = requests.get(sp_url, headers=headers, params={"keys": space_key}, timeout=60)
        if r.status_code >= 400:
            return None
        sj = r.json()
        results = sj.get("results") or []
        if not results:
            return None  # pragma: no cover
        space_id = results[0].get("id")
        if not space_id:
            return None  # pragma: no cover
        pages: List[Dict[str, Any]] = []
        purl = f"{base}/wiki/api/v2/spaces/{space_id}/pages"
        params: Dict[str, Any] = {"limit": 50, "body-format": "storage"}
        next_url: Optional[str] = purl
        while next_url:
            rr = requests.get(
                next_url,
                headers=headers,
                params=params if next_url == purl else None,
                timeout=120,
            )
            if rr.status_code >= 400:
                return None  # pragma: no cover
            js = rr.json()
            for it in js.get("results", []):
                if it.get("status") not in (None, "current", "draft"):
                    continue  # pragma: no cover
                lab_txt = ""
                if label:
                    labs = it.get("labels", {}).get("results", it.get("labels") or [])  # pragma: no cover
                    if isinstance(labs, list):  # pragma: no cover
                        lab_txt = ",".join(  # pragma: no cover
                            str(x.get("name", x) if isinstance(x, dict) else x) for x in labs
                        )
                    if label.lower() not in lab_txt.lower():  # pragma: no cover
                        continue  # pragma: no cover
                body_val = ""
                body = it.get("body") or {}
                if isinstance(body, dict):
                    body_val = (body.get("storage") or body.get("view") or {}).get("value", "") or body.get(
                        "value", ""
                    )
                if len(body_val) < 200:
                    continue  # pragma: no cover
                pid = it.get("id", "")
                pages.append(
                    {
                        "title": it.get("title", ""),
                        "space": space_key,
                        "labels": lab_txt,
                        "author": "",
                        "last_modified": it.get("version", {}).get("createdAt", "")
                        if isinstance(it.get("version"), dict)
                        else "",
                        "parent_page": "",
                        "page_url": f"{base}/wiki/spaces/{space_key}/pages/{pid}",
                        "body": body_val,
                    }
                )
            links = js.get("_links", {}) or {}
            nxt = links.get("next")
            if nxt:
                next_url = base.rstrip("/") + nxt if nxt.startswith("/") else nxt  # pragma: no cover
                params = {}  # pragma: no cover
            else:
                next_url = None
        return pages if pages else None
    except Exception as exc:  # pragma: no cover
        logger.debug("Confluence v2 fetch failed, using v1: %s", exc)  # pragma: no cover
        return None  # pragma: no cover


def fetch_confluence_pages(space_key: str, label: str = "") -> List[Dict[str, Any]]:
    if requests is None:
        raise RuntimeError("requests not installed; pip install requests")  # pragma: no cover
    base = os.environ.get("CONFLUENCE_URL", "").strip().rstrip("/")
    token = os.environ.get("CONFLUENCE_TOKEN", "").strip()
    if not base or not token:
        raise RuntimeError("CONFLUENCE_URL and CONFLUENCE_TOKEN must be set")
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    v2 = _fetch_confluence_pages_v2(base, headers, space_key, label)
    if v2 is not None:
        return v2  # pragma: no cover
    url = f"{base}/wiki/rest/api/content"
    params: Dict[str, Any] = {"spaceKey": space_key, "limit": 50, "expand": "body.storage,version,metadata.labels"}
    pages: List[Dict[str, Any]] = []
    while url:
        r = requests.get(url, headers=headers, params=params, timeout=120)
        r.raise_for_status()
        js = r.json()
        for it in js.get("results", []):
            if it.get("status") != "current":
                continue  # pragma: no cover
            labels = it.get("metadata", {}).get("labels", {}).get("results", [])
            lab_txt = ",".join(x.get("name", "") for x in labels)
            if label and label.lower() not in lab_txt.lower():
                continue  # pragma: no cover
            pages.append(
                {
                    "title": it.get("title", ""),
                    "space": space_key,
                    "labels": lab_txt,
                    "author": it.get("version", {}).get("by", {}).get("displayName", ""),
                    "last_modified": it.get("version", {}).get("when", ""),
                    "parent_page": "",
                    "page_url": f"{base}/wiki/spaces/{space_key}/pages/{it.get('id')}",
                    "body": (it.get("body", {}).get("storage", {}) or {}).get("value", ""),
                }
            )
        nxt = (js.get("_links", {}) or {}).get("next")
        if nxt:
            url = base.rstrip("/") + nxt if nxt.startswith("/") else nxt
            params = {}
        else:
            url = None
    return pages


def _embed_serialize_on() -> bool:
    return os.environ.get("EMBED_SERIALIZE", "0").strip().lower() in ("1", "true", "yes")


def _ollama_embed_url() -> str:
    base = os.environ.get("OLLAMA_HOST", "127.0.0.1:11434").strip()
    if base.startswith("http://") or base.startswith("https://"):
        return base.rstrip("/") + "/api/embed"
    return f"http://{base}/api/embed"


def _ollama_generate_url() -> str:
    """Ollama /api/generate for LLM metadata enrichment."""
    custom = os.environ.get("ENRICH_OLLAMA_URL", "").strip()
    if custom:
        c = custom.rstrip("/")
        return c if c.endswith("/api/generate") else c + "/api/generate"
    base = os.environ.get("OLLAMA_HOST", "127.0.0.1:11434").strip()
    if base.startswith("http://") or base.startswith("https://"):
        return base.rstrip("/") + "/api/generate"
    return f"http://{base}/api/generate"


_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


def _extract_balanced_json_object(text: str) -> Optional[str]:
    """If the model wraps JSON in prose, take the first top-level {...} substring."""
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    for i in range(start, len(text)):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def _parse_ollama_enrichment_json(inner: str) -> Optional[Dict[str, str]]:
    """Parse model JSON into flat llm_* strings; return None on failure."""
    inner = inner.strip()
    m = _JSON_FENCE_RE.search(inner)
    if m:
        inner = m.group(1).strip()
    candidates = [inner]
    blob = _extract_balanced_json_object(inner)
    if blob and blob not in candidates:
        candidates.append(blob)
    obj = None
    for cand in candidates:
        try:
            obj = json.loads(cand)
            break
        except json.JSONDecodeError:
            continue
    if obj is None:
        return None
    if not isinstance(obj, dict):
        return None
    summary = str(obj.get("summary") or "").strip()
    tags_raw = obj.get("tags") or []
    if isinstance(tags_raw, str):
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
    elif isinstance(tags_raw, list):
        tags = [str(t).strip() for t in tags_raw if str(t).strip()]
    else:
        tags = []
    rel_raw = obj.get("related_functions") or obj.get("related_function") or []
    if isinstance(rel_raw, str):
        rel = [t.strip() for t in rel_raw.split(",") if t.strip()]
    elif isinstance(rel_raw, list):
        rel = [str(t).strip() for t in rel_raw if str(t).strip()]
    else:
        rel = []
    tags = tags[:3]
    physics_raw = obj.get("physics_model")
    if physics_raw is None:
        physics = ""
    elif isinstance(physics_raw, str):
        physics = physics_raw.strip()
    elif isinstance(physics_raw, (int, float, bool)):
        physics = str(physics_raw).strip()
    else:
        physics = ""  # lists/objects from malformed JSON — do not stringify into metadata
    return {
        "llm_summary": summary,
        "llm_tags": ",".join(tags),
        "llm_relations": ",".join(rel),
        "llm_physics_model": physics,
    }


def _generate_llm_metadata(
    chunk_text: str,
    chunk_name: str,
    model: str,
    *,
    timeout_sec: float = 120.0,
) -> Dict[str, str]:
    """
    Call local Ollama /api/generate to produce llm_summary, llm_tags, llm_relations, llm_physics_model.
    On HTTP/JSON failure after retries, returns empty strings for all four.
    """
    empty = {"llm_summary": "", "llm_tags": "", "llm_relations": "", "llm_physics_model": ""}
    snippet = chunk_text[:3000]
    safe_chunk_label = json.dumps((chunk_name or "")[:500], ensure_ascii=True)
    prompt = (
        f"You are an expert in Semiconductor Physics and EDA C-programming. "
        f"Analyze this C code chunk named {safe_chunk_label} from the Ngspice circuit simulator.\n"
        f"Code:\n{snippet}\n\n"
        "Respond with a JSON object only, with these keys:\n"
        "  summary: one-line plain-English description of what this chunk computes or models.\n"
        "  tags: array of up to 3 short strings. Prefer physics/math terms "
        "(e.g. 'ebers-moll', 'channel-charge', 'MNA-stamp', 'Newton-Raphson', 'BSIM4') "
        "over generic software terms.\n"
        "  related_functions: array of C function or symbol names called or referenced.\n"
        "  physics_model: (string or null) the semiconductor model or physical equation "
        "being implemented, if identifiable (e.g. 'Shockley diode equation', "
        "'BSIM3 surface potential', 'Ebers-Moll BJT', 'Fowler-Nordheim tunneling')."
    )
    url = _ollama_generate_url()
    payload_obj: Dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1},
    }
    if os.environ.get("ENRICH_JSON_FORMAT", "1").strip().lower() not in ("0", "false", "no"):
        payload_obj["format"] = "json"
    payload = json.dumps(payload_obj).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                data = json.load(resp)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            log_fn = logger.warning if attempt >= 2 else logger.debug
            log_fn(
                "enrich-metadata: Ollama HTTP %s (attempt %s): %s",
                exc.code,
                attempt + 1,
                body[:500],
            )
            if attempt == 2:
                return empty
            continue
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            log_fn = logger.warning if attempt >= 2 else logger.debug
            log_fn("enrich-metadata: Ollama request failed (attempt %s): %s", attempt + 1, exc)
            if attempt == 2:
                return empty
            continue
        except Exception as exc:  # pragma: no cover
            log_fn = logger.warning if attempt >= 2 else logger.debug
            log_fn("enrich-metadata: unexpected error (attempt %s): %s", attempt + 1, exc)
            if attempt == 2:
                return empty
            continue

        raw = data.get("response")
        if raw is None or not isinstance(raw, str):
            log_fn = logger.warning if attempt >= 2 else logger.debug
            log_fn("enrich-metadata: missing response field (attempt %s)", attempt + 1)
            if attempt == 2:
                return empty
            continue
        parsed = _parse_ollama_enrichment_json(raw)
        if parsed is not None:
            return parsed
        if attempt >= 2:
            logger.warning("enrich-metadata: JSON parse failed after %s attempts", attempt + 1)
        else:
            logger.debug("enrich-metadata: JSON parse failed (attempt %s)", attempt + 1)
        if attempt == 2:
            return empty
        continue
    return empty


def _nvidia_total_vram_mb() -> Optional[int]:
    try:
        proc = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return None
        lines = [x.strip() for x in proc.stdout.strip().splitlines() if x.strip()]
        if not lines:
            return None
        return int(float(lines[0]))
    except Exception:
        return None


def _host_total_ram_mb() -> Optional[int]:
    """Best-effort system RAM (MiB). Linux: /proc/meminfo; macOS: sysctl."""
    try:
        if sys.platform == "darwin":
            out = subprocess.run(
                ["sysctl", "-n", "hw.memsize"],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
            if out.returncode != 0 or not out.stdout.strip():
                return None
            return int(int(out.stdout.strip()) // (1024 * 1024))
        p = Path("/proc/meminfo")
        if p.is_file():
            for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.startswith("MemTotal:"):
                    parts = line.split()
                    if len(parts) >= 2:
                        return int(parts[1]) // 1024  # kB -> MiB
    except Exception:
        return None
    return None


def resolve_embed_ingest_settings() -> Tuple[int, int, int]:
    """Return (batch_size, worker_threads, async_concurrency) with optional VRAM + RAM scaling."""
    cpu = os.cpu_count() or 2
    default_workers = min(4, max(2, cpu))
    batch = int(os.environ.get("EMBED_BATCH_SIZE", "16"))
    workers = int(os.environ.get("EMBED_WORKERS", str(default_workers)))
    conc = int(os.environ.get("EMBED_CONCURRENCY", str(max(2, min(8, workers * 2)))))
    batch_env_set = "EMBED_BATCH_SIZE" in os.environ
    conc_env_set = "EMBED_CONCURRENCY" in os.environ

    vram = _nvidia_total_vram_mb()
    if vram is not None:
        if vram >= 12000:
            batch = max(batch, 24)
            conc = max(conc, 6)
        elif vram >= 8000:
            batch = max(batch, 20)
            conc = max(conc, 4)
        logger.info(
            "Embedding autoscale: VRAM ~%d MiB -> batch=%d concurrency=%d workers=%d",
            vram,
            batch,
            conc,
            workers,
        )

    ram = _host_total_ram_mb()
    if ram is not None:
        if ram < 4096:
            batch = min(batch, 6)
            conc = min(conc, 2)
        elif ram < 8192:
            batch = min(batch, 12)
            conc = min(conc, 4)
        elif ram >= 32768 and not batch_env_set and not conc_env_set:
            batch = max(batch, 20)
            conc = max(conc, 8)
        logger.info(
            "Embedding autoscale: RAM ~%d MiB -> batch=%d concurrency=%d workers=%d",
            ram,
            batch,
            conc,
            workers,
        )

    return max(1, batch), max(1, workers), max(1, conc)


def http_embed_documents_batch(model: str, texts: List[str], timeout: float = 300.0) -> List[List[float]]:
    """Direct Ollama /api/embed (avoids shared LangChain client across threads)."""
    url = _ollama_embed_url()
    payload = json.dumps({"model": model, "input": texts}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        raise RuntimeError(f"Ollama embed HTTP {exc.code}: {body}") from exc
    embs = data.get("embeddings")
    if embs is not None:
        return embs
    one = data.get("embedding")
    if one is not None:
        return [one]
    raise RuntimeError(f"Unexpected Ollama embed response: {list(data.keys())}")


def embed_with_retry(embedder: OllamaEmbeddings, batch: List[str]) -> Optional[List[List[float]]]:
    def _try(b: List[str]) -> Optional[List[List[float]]]:
        for _ in range(MAX_RETRIES):
            try:
                if _embed_serialize_on():
                    with _embed_lock:
                        return embedder.embed_documents(b)
                return embedder.embed_documents(b)
            except Exception as exc:
                logger.warning("embed retry: %s", exc)
                time.sleep(EMBED_BACKOFF_SEC)
        if len(b) <= 1:
            return None
        mid = max(1, len(b) // 2)
        a = _try(b[:mid])
        b2 = _try(b[mid:])
        if a is None or b2 is None:
            return None
        return a + b2

    return _try(batch)


def embed_with_retry_http(model: str, batch: List[str]) -> Optional[List[List[float]]]:
    """HTTP embed with same retry/split semantics as embed_with_retry."""

    def _try(b: List[str]) -> Optional[List[List[float]]]:
        for _ in range(MAX_RETRIES):
            try:
                if _embed_serialize_on():
                    with _embed_lock:
                        return http_embed_documents_batch(model, b)
                return http_embed_documents_batch(model, b)
            except Exception as exc:
                logger.warning("embed http retry: %s", exc)
                time.sleep(EMBED_BACKOFF_SEC)
        if len(b) <= 1:
            return None
        mid = max(1, len(b) // 2)
        a = _try(b[:mid])
        b2 = _try(b[mid:])
        if a is None or b2 is None:
            return None
        return a + b2

    return _try(batch)


# Async batches live in ingest_kit.embedding.http_async


def embedding_worker(
    embed_model: str,
    worker_id: int,
    chunk_q: "queue.Queue[Optional[List[Tuple[str, str, Dict[str, str]]]]]",
    result_q: "queue.Queue[Optional[Tuple[List[str], List[str], List[Dict[str, str]], List[List[float]]]]]",
) -> None:
    embedder = OllamaEmbeddings(model=embed_model)
    use_http = os.environ.get("EMBED_HTTP", "1").strip().lower() not in ("0", "false", "no")
    while True:
        item = chunk_q.get()
        if item is None:
            chunk_q.task_done()
            break
        try:
            ids, texts, metas = [], [], []
            for cid, text, meta in item:
                ids.append(cid)
                texts.append(text)
                metas.append(meta)
            if use_http:
                vecs = embed_with_retry_http(embed_model, texts)
            else:
                vecs = embed_with_retry(embedder, texts)
            if vecs is None:
                srcs = [m.get("source", "") for m in metas[:5]]
                logger.error(
                    "embedding failed permanently worker=%d batch=%d sample_sources=%s",
                    worker_id,
                    len(texts),
                    srcs,
                )
                result_q.put(None)
            else:
                result_q.put((ids, texts, metas, vecs))
        except Exception as exc:  # pragma: no cover
            logger.exception("worker error: %s", exc)  # pragma: no cover
            result_q.put(None)  # pragma: no cover
        finally:
            chunk_q.task_done()


def migrate_old_checkpoint(db_path: Path, collection_name: str) -> None:
    """One-time migration from legacy flat checkpoint file to per-collection ingest_checkpoint.json."""
    old_path = db_path / "ingestion_checkpoint.json"
    new_path = db_path / "ingest_checkpoint.json"
    if not old_path.exists() or new_path.exists():
        return
    try:
        with open(old_path, encoding="utf-8") as fh:
            old_data = json.load(fh)
        if not isinstance(old_data, dict):
            return
        cp_key = f"{collection_name}::checkpoint"
        new_data = {cp_key: json.dumps(old_data)}
        with open(new_path, "w", encoding="utf-8") as fh:
            json.dump(new_data, fh, indent=2)
        logger.info(
            "Migrated legacy checkpoint %s (%d entries) -> %s",
            old_path.name,
            len(old_data),
            new_path.name,
        )
    except Exception as exc:
        logger.warning("Checkpoint migration failed: %s", exc)


def load_checkpoint(db_path: Path) -> Dict[str, str]:
    p = db_path / "ingest_checkpoint.json"
    if not p.exists():
        return {}
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def save_checkpoint(db_path: Path, data: Dict[str, str]) -> None:
    p = db_path / "ingest_checkpoint.json"
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


def append_manifest(db_path: Path, record: Dict[str, Any]) -> None:
    p = db_path / "ingestion_history.jsonl"
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def write_ingestion_config(db_path: Path, model: str) -> None:
    cfg = {"embedding_model": model, "ingestion_version": INGESTION_VERSION}
    with open(db_path / "ingestion_config.json", "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2)



def validate_embedding_dimension(
    coll: Any,
    embedder: OllamaEmbeddings,
    collection_name: str,
    embed_model: str,
) -> Optional[str]:
    """If the collection already has vectors, ensure *embed_model* matches their dimension.

    Returns a human-readable error string, or None when OK / when no check applies.
    """
    schema_dim: Optional[int] = None
    try:
        m = getattr(coll, "_model", None)
        if m is not None:
            raw = getattr(m, "dimension", None)
            if raw is not None and int(raw) > 0:
                schema_dim = int(raw)
    except Exception:  # pragma: no cover
        schema_dim = None  # pragma: no cover

    try:
        n = int(coll.count())
    except Exception:
        return None
    if n == 0:
        if schema_dim is not None:
            try:
                probe = embedder.embed_query("__dimension_probe__")
                probe_dim = len(probe)
            except Exception as exc:
                return f"Could not probe embedding model {embed_model!r}: {exc}"
            if schema_dim != probe_dim:
                return (
                    f"Embedding dimension mismatch for collection {collection_name!r}: "
                    f"collection schema expects {schema_dim} dimensions but model "
                    f"{embed_model!r} produces {probe_dim}. Re-ingest with the original "
                    f"model, or delete this collection first "
                    f"(e.g. nomic-embed-text → 768, mxbai-embed-large → 1024)."
                )
        return None
    try:
        rows = coll.get(limit=1, include=["embeddings"])
        embs = rows.get("embeddings") or []
        emb0 = embs[0] if embs else None
        if not embs or emb0 is None:
            return None
        existing_dim = len(emb0)
    except Exception:
        return None
    try:
        probe = embedder.embed_query("__dimension_probe__")
        probe_dim = len(probe)
    except Exception as exc:  # pragma: no cover
        return f"Could not probe embedding model {embed_model!r}: {exc}"  # pragma: no cover
    if existing_dim != probe_dim:
        return (
            f"Embedding dimension mismatch for collection {collection_name!r}: "
            f"existing index uses {existing_dim} dimensions but model {embed_model!r} "
            f"produces {probe_dim}. Re-ingest with the same model as the original index "
            f"(e.g. nomic-embed-text → 768, mxbai-embed-large → 1024), or delete this "
            f"collection / use a fresh VectorDB before switching embedding models."
        )
    return None


def update_repos_manifest(db_path: Path, collection_name: str, repo_counts: Dict[str, int]) -> None:
    path = db_path / "repos_manifest.json"
    data: Dict[str, Any] = {}
    if path.exists():
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception:
            data = {}
    if "by_collection" not in data or not isinstance(data["by_collection"], dict):
        data["by_collection"] = {}
    data["by_collection"][collection_name] = repo_counts
    if collection_name.endswith("_code"):
        for k, v in repo_counts.items():
            data[k] = v
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


def print_status_dashboard(db_path: Path) -> None:
    print("=" * 64)
    print("            DOMAIN RAG — KNOWLEDGE BASE STATUS")
    print("=" * 64)
    client = chromadb.PersistentClient(path=str(db_path))
    cols = client.list_collections()
    concept_counts: Counter[str] = Counter()
    rows = []
    for c in sorted(cols, key=lambda x: x.name):
        coll = client.get_collection(c.name)
        n = _safe_count(coll)
        if n == 0:
            rows.append((c.name, 0, 0, ""))  # pragma: no cover
            continue  # pragma: no cover
        sample = coll.get(include=["metadatas"], limit=min(n, 8000))
        metas = sample.get("metadatas") or []
        sources = {str(m.get("source", "")) for m in metas if m}
        for m in metas:
            if not m:
                continue  # pragma: no cover
            cs = m.get("concepts", "")
            if cs:
                for part in iter_concept_ids(str(cs)):
                    concept_counts[part] += 1
        dates = [str(m.get("ingestion_date", "")) for m in metas if m and m.get("ingestion_date")]
        last_ing = max(dates) if dates else ""
        rows.append((c.name, n, len(sources), last_ing))
    hdr = f"{'Collection':<22} {'Chunks':>8} {'Sources':>8} {'Last Ingested':<22}"
    print(hdr)
    print("-" * 64)
    for name, n, sc, li in rows:
        print(f"{name:<22} {n:>8,} {sc:>8} {li:<22}")
    print("=" * 64)
    top = concept_counts.most_common(15)
    if top:
        print("Top concepts:", ", ".join(f"{k}({v})" for k, v in top))


def _respect_gitignore() -> bool:
    return os.environ.get("RESPECT_GITIGNORE", "1").strip().lower() not in ("0", "false", "no")


def _gitignore_parent_chain_dirs(rel_posix: str) -> List[str]:
    """Parent directories (posix paths from repo root) whose `.gitignore` may apply to *rel_posix*."""
    rel_posix = rel_posix.replace("\\", "/").strip("/")
    parts = [p for p in rel_posix.split("/") if p]
    if not parts:
        return [""]
    dirs: List[str] = [""]
    for i in range(len(parts) - 1):
        dirs.append("/".join(parts[: i + 1]))
    return dirs


def _relpath_under_gitignore_dir(dir_rel: str, full_rel_posix: str) -> str:
    if not dir_rel:
        return full_rel_posix
    prefix = dir_rel + "/"
    if not full_rel_posix.startswith(prefix):
        return full_rel_posix
    return full_rel_posix[len(prefix) :]


def _gitignore_file_path(root_dir: Path, dir_rel_posix: str) -> Path:
    if not dir_rel_posix:
        return root_dir / ".gitignore"
    return root_dir.joinpath(*dir_rel_posix.split("/")) / ".gitignore"


def _read_gitignore_spec_for_dir(root_dir: Path, dir_rel_posix: str, cache: Dict[str, Any]) -> Optional[Any]:
    if dir_rel_posix in cache:
        return cache[dir_rel_posix]
    if not _respect_gitignore() or pathspec is None:
        cache[dir_rel_posix] = None
        return None
    gi = _gitignore_file_path(root_dir, dir_rel_posix)
    if not gi.is_file():
        cache[dir_rel_posix] = None
        return None
    try:
        lines = gi.read_text(encoding="utf-8", errors="replace").splitlines()
        spec = pathspec.PathSpec.from_lines("gitwildmatch", lines)
        cache[dir_rel_posix] = spec
        return spec
    except Exception:
        cache[dir_rel_posix] = None
        return None


def _path_matches_any_nested_gitignore(
    root_dir: Path,
    rel_posix: str,
    cache: Dict[str, Any],
    *,
    is_dir: bool,
) -> bool:
    """True if any ancestor `.gitignore` excludes this path (Git-style, per-directory rules)."""
    if not _respect_gitignore() or pathspec is None:
        return False
    rel_norm = rel_posix.replace("\\", "/").strip("/")
    for drel in _gitignore_parent_chain_dirs(rel_norm):
        spec = _read_gitignore_spec_for_dir(root_dir, drel, cache)
        if spec is None:
            continue
        rel_for_spec = _relpath_under_gitignore_dir(drel, rel_norm)
        candidates = [rel_for_spec + "/", rel_for_spec] if is_dir else [rel_for_spec]
        for cand in candidates:
            if not cand:
                continue
            try:
                if spec.match_file(cand):
                    return True
            except Exception:
                continue
    return False


def _load_gitignore_spec(root: Path) -> Any:
    """Load only the repository root `.gitignore` (tests and simple callers)."""
    c: Dict[str, Any] = {}
    return _read_gitignore_spec_for_dir(root.resolve(), "", c)


def git_checkpoint_head_key(collection_name: str) -> str:
    return f"{collection_name}::git_head"


def _git_run(root: Path, *git_args: str, timeout: float = 120.0) -> Tuple[int, str, str]:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), *git_args],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return proc.returncode, (proc.stdout or "").strip(), (proc.stderr or "").strip()
    except FileNotFoundError:
        return 127, "", "git not found"
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"


def git_diff_file_sets(
    root: Path, base_ref: str
) -> Tuple[Optional[Set[str]], Optional[Set[str]], Optional[str]]:
    """Return (modified_paths, deleted_paths, head_sha) relative to *root*, or Nones if unusable."""
    code, _, _ = _git_run(root, "rev-parse", "--is-inside-work-tree")
    if code != 0:
        return None, None, None
    hc, head_out, _ = _git_run(root, "rev-parse", "HEAD")
    if hc != 0 or not head_out:
        return None, None, None
    head_sha = head_out.splitlines()[0].strip()

    def collect(diff_filter: str) -> Set[str]:
        rc, out, _ = _git_run(
            root,
            "diff",
            "--name-only",
            f"--diff-filter={diff_filter}",
            f"{base_ref}...HEAD",
        )
        if rc != 0:
            rc, out, _ = _git_run(
                root,
                "diff",
                "--name-only",
                f"--diff-filter={diff_filter}",
                base_ref,
                head_sha,
            )
        if rc != 0:
            return set()
        return {ln.strip().replace("\\", "/") for ln in out.splitlines() if ln.strip()}

    return collect("ACMR"), collect("D"), head_sha


def iter_files(
    root: Path,
    exts: Optional[set] = None,
    skip_dirs: Optional[set] = None,
    skip_exts: Optional[set] = None,
) -> List[Path]:
    root_dir = root.resolve()
    gi_cache: Dict[str, Any] = {}
    if root.is_file():
        p = root
        suf = p.suffix.lower()
        if skip_exts and suf in skip_exts:
            return []  # pragma: no cover
        if exts and suf not in exts:
            return []  # pragma: no cover
        return [p]
    out: List[Path] = []
    for dirpath, dirnames, files in os.walk(root_dir):
        if skip_dirs:
            dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        if _respect_gitignore() and pathspec is not None:
            try:
                rel_parent = Path(dirpath).resolve().relative_to(root_dir).as_posix()
            except ValueError:
                rel_parent = ""
            dirnames[:] = [
                d
                for d in dirnames
                if not _path_matches_any_nested_gitignore(
                    root_dir,
                    f"{rel_parent}/{d}" if rel_parent else d,
                    gi_cache,
                    is_dir=True,
                )
            ]
        for fn in files:
            p = Path(dirpath) / fn
            suf = p.suffix.lower()
            if skip_exts and suf in skip_exts:
                continue
            if exts and suf not in exts:
                continue
            if _respect_gitignore() and pathspec is not None:
                try:
                    rel = p.resolve().relative_to(root_dir).as_posix()
                    if _path_matches_any_nested_gitignore(root_dir, rel, gi_cache, is_dir=False):
                        continue
                except Exception:
                    pass  # pragma: no cover
            out.append(p)
    return sorted(out)


def load_rally_rows_from_csv(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8", errors="replace") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            rows.append({(k or "").strip(): (v if v is not None else "") for k, v in row.items()})
    return rows


def _ingest_run_impl(args: argparse.Namespace) -> int:
    t0 = time.time()
    setup_logging(args.verbose)
    db_path = Path(args.db_path).resolve()
    db_path.mkdir(parents=True, exist_ok=True)

    if args.mode == "status":
        print_status_dashboard(db_path)
        return 0

    domain = args.domain or "general"
    collection_name = resolve_collection(args.mode, domain, args.collection)
    migrate_old_checkpoint(db_path, collection_name)
    cp_key = f"{collection_name}::checkpoint"
    source_type_map = {
        "code": "code",
        "domain": "domain_doc",
        "rfc": "rfc",
        "rally": "rally",
        "customer": "customer",
        "mib": "mib",
        "wiki": "wiki",
        "release-notes": "release_notes",
        "theory": "theory",
        "community": "community",
    }
    source_type = source_type_map.get(args.mode, "domain_doc")
    rally_filter_rules = parse_rally_filter(getattr(args, "rally_filter", None))

    concept_registry = load_concept_registry(Path(args.concept_registry))

    embed_model = os.environ.get("EMBEDDING_MODEL", "nomic-embed-text").strip()
    embedder = OllamaEmbeddings(model=embed_model)

    client = chromadb.PersistentClient(path=str(db_path))
    coll = client.get_or_create_collection(name=collection_name)

    dim_err = validate_embedding_dimension(coll, embedder, collection_name, embed_model)
    if dim_err:
        if getattr(args, "recreate_collection", False):
            logger.warning(
                "Deleting collection %r and its ingest checkpoint so it can be rebuilt "
                "with model %r (%s)",
                collection_name,
                embed_model,
                dim_err,
            )
            try:
                client.delete_collection(name=collection_name)
            except Exception as exc:  # pragma: no cover
                logger.error("delete_collection failed: %s", exc)  # pragma: no cover
                return 2  # pragma: no cover
            coll = client.get_or_create_collection(name=collection_name)
            ck = load_checkpoint(db_path)
            ck.pop(cp_key, None)
            save_checkpoint(db_path, ck)
            dim_err = validate_embedding_dimension(coll, embedder, collection_name, embed_model)
            if dim_err:
                logger.error("After recreate, embedding check still failed: %s", dim_err)  # pragma: no cover
                return 2  # pragma: no cover
        else:
            logger.error("%s", dim_err)  # pragma: no cover
            logger.error(  # pragma: no cover
                "To rebuild collection %r with the current model, pass --recreate-collection "
                "(removes all vectors in that collection and clears its ingest checkpoint).",
                collection_name,
            )
            return 2  # pragma: no cover

    write_ingestion_config(db_path, embed_model)

    checkpoint = load_checkpoint(db_path)
    file_hashes: Dict[str, str] = {}
    if not args.force and cp_key in checkpoint:
        try:
            file_hashes = json.loads(checkpoint[cp_key])
        except Exception:  # pragma: no cover
            file_hashes = {}  # pragma: no cover

    files_to_process: List[Tuple[Path, Dict[str, Any]]] = []
    root: Optional[Path] = Path(args.source).resolve() if args.source else None
    git_head_key = git_checkpoint_head_key(collection_name)
    stored_git_head = checkpoint.get(git_head_key, "")
    if not isinstance(stored_git_head, str):
        stored_git_head = ""
    new_git_head_commit: Optional[str] = None

    if args.mode == "rally" and root is None:
        if requests is None:
            logger.error("pip install requests for Rally API mode")
            return 2
        if not args.rally_project:
            logger.error("--rally-project required for rally mode without --source")  # pragma: no cover
            return 2  # pragma: no cover
        arts = fetch_rally_artifacts(args.rally_project)
        for obj in arts:
            if not rally_matches_user_filter(obj, rally_filter_rules):
                continue  # pragma: no cover
            sev = str(obj.get("Severity") or "")
            if sev.isdigit() and int(sev) > 3:
                continue  # pragma: no cover
            tags = str(obj.get("Tags") or "")
            if "duplicate" in tags.lower():
                continue  # pragma: no cover
            desc = str(obj.get("Description") or "")
            if not desc.strip():
                continue  # pragma: no cover
            fid = str(obj.get("FormattedID") or "unknown")
            files_to_process.append((Path(fid), {"virtual": True, "rally": obj}))
    elif args.mode == "wiki" and root is None:
        if requests is None:
            logger.error("pip install requests for Confluence wiki mode without --source")  # pragma: no cover
            return 2  # pragma: no cover
        if not args.confluence_space:
            logger.error("--confluence-space required when --source not set")  # pragma: no cover
            return 2  # pragma: no cover
        clabel = getattr(args, "confluence_label", None) or ""
        pages = fetch_confluence_pages(args.confluence_space, clabel)
        for pg in pages:
            body = pg.get("body") or ""
            if len(body) < 200:
                continue  # pragma: no cover
            slug = re.sub(r"\W+", "_", pg.get("title", "page"))[:80] + ".wiki"
            files_to_process.append((Path(slug), {"virtual": True, "wiki": pg}))
    else:
        if root is None:
            env_src = os.environ.get("SOURCE_FOLDER", "").strip()
            if not env_src:
                logger.error("No --source and SOURCE_FOLDER not set")
                return 2
            root = Path(env_src).resolve()  # pragma: no cover
        git_used = False
        if getattr(args, "git_diff", False):
            base_ref = (getattr(args, "git_diff_base", None) or "").strip()
            if not base_ref:
                base_ref = stored_git_head.strip() or "HEAD~1"
            mod_set, del_set, gh = git_diff_file_sets(root, base_ref)
            if mod_set is not None and gh:
                git_used = True
                new_git_head_commit = gh
                git_gi_cache: Dict[str, Any] = {}
                for rel in sorted(del_set or ()):
                    ap = str((root / rel).resolve())
                    try:
                        coll.delete(where={"source": ap})
                    except Exception as exc:
                        logger.warning("git-diff delete chunks for %s: %s", ap, exc)
                    file_hashes.pop(ap, None)
                mib_exts = {".mib", ".my"} if args.mode == "mib" else None
                for rel in sorted(mod_set):
                    p = root / rel
                    if not p.is_file():
                        continue
                    suf = p.suffix.lower()
                    if mib_exts is not None and suf not in mib_exts:
                        continue
                    if args.mode == "code" and suf in IGNORED_EXTS:
                        continue
                    if _respect_gitignore() and pathspec is not None:
                        try:
                            r = p.resolve().relative_to(root.resolve())
                            if _path_matches_any_nested_gitignore(
                                root.resolve(), r.as_posix(), git_gi_cache, is_dir=False
                            ):
                                continue
                        except Exception:
                            pass  # pragma: no cover
                    if args.mode == "rally" and suf == ".csv":
                        try:
                            for row in load_rally_rows_from_csv(p):
                                if not rally_matches_user_filter(row, rally_filter_rules):
                                    continue  # pragma: no cover
                                fid = str(
                                    row.get("FormattedID")
                                    or row.get("formatted_id")
                                    or row.get("ID")
                                    or row.get("id")
                                    or hashlib.md5(str(row).encode()).hexdigest()[:10]
                                )
                                files_to_process.append(
                                    (
                                        Path(fid),
                                        {
                                            "virtual": True,
                                            "rally": row,
                                            "_csv_path": str(p.resolve()),
                                        },
                                    )
                                )
                        except Exception as exc:  # pragma: no cover
                            logger.warning("CSV rally skip %s: %s", p, exc)  # pragma: no cover
                        continue
                    files_to_process.append((p, {"virtual": False}))
            else:
                logger.warning(
                    "git-diff: repository unusable or diff failed; falling back to full directory scan"
                )
        if not git_used:
            if args.mode == "mib":
                paths = iter_files(root, {".mib", ".my"}, skip_dirs=IGNORED_DIRS)
            elif args.mode == "code":
                paths = iter_files(root, None, skip_dirs=IGNORED_DIRS, skip_exts=IGNORED_EXTS)
            else:
                paths = iter_files(root, None, skip_dirs=IGNORED_DIRS)
        else:
            paths = []
        # GUI / first-time ingest: --git-diff with an empty change set still leaves git_used True and
        # paths=[], so nothing is scanned. If the tree actually has files, fall back to a full walk
        # unless GIT_DIFF_FALLBACK_FULL=0 (strict incremental-only).
        _git_diff_fb = os.environ.get("GIT_DIFF_FALLBACK_FULL", "1").strip().lower() not in (
            "0",
            "false",
            "no",
        )
        if (
            _git_diff_fb
            and getattr(args, "git_diff", False)
            and git_used
            and not files_to_process
            and root is not None
            and root.is_dir()
        ):
            if args.mode == "mib":
                probe = iter_files(root, {".mib", ".my"}, skip_dirs=IGNORED_DIRS)
            elif args.mode == "code":
                probe = iter_files(root, None, skip_dirs=IGNORED_DIRS, skip_exts=IGNORED_EXTS)
            else:
                probe = iter_files(root, None, skip_dirs=IGNORED_DIRS)
            if probe:
                logger.warning(
                    "git-diff matched no files, but %d path(s) exist under --source; "
                    "running full directory scan (set GIT_DIFF_FALLBACK_FULL=0 to disable).",
                    len(probe),
                )
                paths = probe
        for p in paths:
            if args.mode == "rally" and p.suffix.lower() == ".csv":
                try:
                    for row in load_rally_rows_from_csv(p):
                        if not rally_matches_user_filter(row, rally_filter_rules):
                            continue  # pragma: no cover
                        fid = str(
                            row.get("FormattedID")
                            or row.get("formatted_id")
                            or row.get("ID")
                            or row.get("id")
                            or hashlib.md5(str(row).encode()).hexdigest()[:10]
                        )
                        files_to_process.append(
                            (
                                Path(fid),
                                {
                                    "virtual": True,
                                    "rally": row,
                                    "_csv_path": str(p.resolve()),
                                },
                            )
                        )
                except Exception as exc:  # pragma: no cover
                    logger.warning("CSV rally skip %s: %s", p, exc)  # pragma: no cover
            else:
                files_to_process.append((p, {"virtual": False}))

    chunks_deleted = 0
    if file_hashes:
        physical_keys = {str(p[0].resolve()) for p in files_to_process if not p[1].get("virtual")}
        for old in list(file_hashes.keys()):
            if old in physical_keys or old.startswith("rally:") or old.startswith(("http://", "https://")):
                continue
            if old.startswith("csv:"):  # pragma: no cover
                rest = old[4:]  # pragma: no cover
                ri = rest.rfind(":")  # pragma: no cover
                csvp = rest[:ri] if ri > 0 else rest  # pragma: no cover
                if os.path.isfile(csvp):  # pragma: no cover
                    continue  # pragma: no cover
            elif os.path.isfile(old):  # pragma: no cover
                continue  # pragma: no cover
            if getattr(args, "clean_stale", False):  # pragma: no cover
                try:  # pragma: no cover
                    coll.delete(where={"source": old})  # pragma: no cover
                    chunks_deleted += 1  # pragma: no cover
                except Exception as exc:  # pragma: no cover
                    logger.warning("stale delete failed %s: %s", old, exc)  # pragma: no cover
            del file_hashes[old]  # pragma: no cover

    repo_file_counts: Counter[str] = Counter()
    root_for_rel = root if root is not None else Path(".").resolve()

    def rel_repo_for(path: Path) -> Tuple[str, str]:
        try:
            rel = path.resolve().relative_to(root_for_rel.resolve())
        except Exception:  # pragma: no cover
            return "root", str(path)  # pragma: no cover
        parts = rel.parts
        if len(parts) > 1:
            return parts[0], str(Path(*parts[1:]))  # pragma: no cover
        return "root", parts[0] if parts else str(path)

    work_items: List[Tuple[str, str, Dict[str, str]]] = []
    vocab_tokens: set[str] = set()
    concepts_found: Counter[str] = Counter()
    ctype_dist: Counter[str] = Counter()
    results_holder: Dict[str, Any] = {
        "processed": 0,
        "failed": 0,
        "errors": [],
        "chunks_created": 0,
        "chunks_updated": 0,
    }
    files_processed = 0
    # Progress lines while --enrich-metadata runs (many Ollama calls per file; tqdm only advances per file).
    _enrich_hb_sec = float(os.environ.get("INGEST_ENRICH_HEARTBEAT_SEC", "20"))
    _enrich_hb_next = 0.0

    ingestion_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if (
        not files_to_process
        and root is not None
        and root.is_dir()
        and args.mode not in ("status", "rally", "wiki")
    ):
        logger.error(
            "No ingestible files under --source %s for mode=%s. "
            "Is the directory empty or a placeholder? Clone sources into this path, or point "
            "--source at a checkout that contains files. If --git-diff is on, try turning it off. "
            "If files exist but are skipped, try RESPECT_GITIGNORE=0.",
            root,
            args.mode,
        )

    # Structural importance: count incoming references per file stem (code mode only).
    file_ref_counts: Dict[str, int] = {}
    if args.mode == "code":
        file_ref_counts = build_file_ref_counts_for_code_ingest(files_to_process)

    for path, extra in _tqdm_ingest(
        files_to_process, desc="Scanning", unit="file", total=len(files_to_process)
    ):
        file_deps_str = ""
        effective_source_type = source_type
        if shutdown_event.is_set():
            break  # pragma: no cover
        if extra.get("virtual"):
            if "rally" in extra:
                obj = extra["rally"]
                if extra.get("_csv_path"):
                    rid = str(
                        obj.get("FormattedID")
                        or obj.get("formatted_id")
                        or obj.get("id")
                        or obj.get("ID")
                        or path.name
                    )
                    src_key = f"csv:{extra['_csv_path']}:{rid}"
                else:
                    src_key = f"rally:{obj.get('FormattedID')}"
                if not rally_matches_user_filter(obj, rally_filter_rules):
                    continue  # pragma: no cover
                blob = json.dumps(obj, sort_keys=True)
                h = hashlib.md5(blob.encode()).hexdigest()
                if not args.force and file_hashes.get(src_key) == h:
                    continue  # pragma: no cover
                pieces = chunk_rally_ticket(obj, src_key)
            elif "wiki" in extra:
                pg = extra["wiki"]
                src_key = str(pg.get("page_url") or pg.get("title"))
                h = hashlib.md5(str(pg.get("body")).encode()).hexdigest()
                if not args.force and file_hashes.get(src_key) == h:
                    continue  # pragma: no cover
                meta_pg = {
                    "page_title": pg.get("title", ""),
                    "space": pg.get("space", ""),
                    "labels": pg.get("labels", ""),
                    "author": pg.get("author", ""),
                    "last_modified": pg.get("last_modified", ""),
                    "parent_page": pg.get("parent_page", ""),
                    "page_url": pg.get("page_url", ""),
                }
                pieces = chunk_wiki_page(pg.get("body", ""), src_key, meta_pg)
            else:
                continue  # pragma: no cover
            abs_src = src_key
            ext = ".virtual"
            repo = "external"
            rel = abs_src
            mtime = ""
            size_kb = 0.0
        else:
            if not path.is_file():
                continue  # pragma: no cover
            abs_src = str(path.resolve())
            allow_ls_fb = bool(getattr(args, "allow_language_split_fallback", False)) or (
                os.environ.get("INGEST_ALLOW_LANGUAGE_SPLIT_FALLBACK", "").strip().lower()
                in ("1", "true", "yes")
            )
            _sk, chunk_fn, limit_mb, per_file_src_override = choose_strategy_for_path(
                path,
                source_type,
                mib_keep_deprecated=getattr(args, "mib_keep_deprecated", False),
                embed_model=embed_model,
                allow_language_split_fallback=allow_ls_fb,
            )
            effective_source_type = per_file_src_override or source_type
            max_bytes = limit_mb * 1024 * 1024
            st = path.stat()
            if st.st_size > max_bytes:
                logger.warning(  # pragma: no cover
                    "skip large file %s (%d MB > %d MB)",
                    path,
                    st.st_size // 1024 // 1024,
                    limit_mb,
                )
                continue  # pragma: no cover
            h = file_md5(path)
            if not args.force and file_hashes.get(abs_src) == h:
                continue
            content, _enc = read_file_bytes(path)
            if content is None:
                continue  # pragma: no cover
            if args.mode == "customer":
                if sanitize_pii:
                    content = sanitize_pii(content)
                try:
                    obj = json.loads(content)
                    pieces = chunk_customer_ticket(obj, abs_src)
                except Exception:
                    fm, body = parse_frontmatter(content)
                    pieces = chunk_community(body, abs_src, fm)
                    pieces = [
                        (t, {**m, "chunk_strategy": "customer_ticket", "ticket_id": path.stem})
                        for t, m in pieces
                    ]
            elif args.mode == "rally" and path.suffix.lower() == ".csv":
                pieces = []  # pragma: no cover
                for row in load_rally_rows_from_csv(path):  # pragma: no cover
                    if not rally_matches_user_filter(row, rally_filter_rules):  # pragma: no cover
                        continue  # pragma: no cover
                    pieces.extend(chunk_rally_ticket(row, abs_src))  # pragma: no cover
            elif args.mode == "rally" and path.suffix.lower() in (".json", ".md", ".txt"):
                try:
                    obj = json.loads(content)
                    if isinstance(obj, list):
                        pieces = []
                        for it in obj:
                            if not rally_matches_user_filter(it, rally_filter_rules):
                                continue  # pragma: no cover
                            pieces.extend(chunk_rally_ticket(it, abs_src))
                    else:
                        if not rally_matches_user_filter(obj, rally_filter_rules):
                            pieces = []  # pragma: no cover
                        else:
                            pieces = chunk_rally_ticket(obj, abs_src)
                except Exception:
                    pieces = chunk_rally_ticket(
                        {"FormattedID": path.stem, "Description": content, "Name": path.stem},
                        abs_src,
                    )
            elif args.mode == "community":
                fm, body = parse_frontmatter(content)
                pieces = chunk_community(body, abs_src, fm)
            elif args.mode == "wiki" and path.suffix.lower() in (".html", ".htm", ".md"):
                pieces = chunk_wiki_page(content, abs_src, {})
            elif args.mode == "release-notes":
                pieces = chunk_release_notes(content, abs_src)
            elif args.mode == "mib":
                pieces = chunk_mib(content, path, skip_deprecated=not getattr(args, "mib_keep_deprecated", False))
            elif args.mode == "rfc":
                pieces = chunk_rfc(content, abs_src, embed_model=embed_model)
            else:
                try:
                    pieces = chunk_fn(path, content)
                except TreeSitterFallbackDisallowedError as exc:
                    logger.error("%s: %s", abs_src, exc)
                    results_holder["errors"].append(f"{abs_src}: {exc}")
                    continue
            ext = path.suffix.lower()
            repo, rel = rel_repo_for(path)
            mtime = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            size_kb = round(st.st_size / 1024.0, 3)
            file_deps_str = extract_dependencies(content, ext) if effective_source_type == "code" else ""

        if not pieces:
            continue  # pragma: no cover

        if not extra.get("virtual") and abs_src and not args.dry_run:
            try:
                coll.delete(where={"source": abs_src})
            except Exception:  # pragma: no cover
                pass  # pragma: no cover

        base = empty_metadata()
        imp_val = "0"
        if effective_source_type == "code" and not extra.get("virtual") and path.is_file():
            imp_val = str(file_ref_counts.get(path.stem, 0))
        base.update(
            {
                "source": abs_src,
                "source_type": effective_source_type,
                "domain": domain,
                "repository": repo,
                "relative_path": rel,
                "extension": ext,
                "file_size_kb": str(size_kb),
                "last_modified": mtime,
                "ingestion_date": ingestion_ts,
                "ingestion_version": INGESTION_VERSION,
                "dependencies": file_deps_str,
                "device_family": _device_family_for_path(path),
                "structural_importance": imp_val,
            }
        )

        for i, (text, partial) in enumerate(pieces):
            meta = {**base, **partial}
            meta["chunk_index"] = str(partial.get("chunk_index", i))
            ctype = partial.get("content_type") or detect_content_type(text)
            meta["content_type"] = ctype
            ctype_dist[ctype] += 1
            raw_concepts = partial.get("concepts")
            if raw_concepts is not None and str(raw_concepts).strip() != "":
                rc = str(raw_concepts).strip()  # pragma: no cover
                concepts = rc if rc.startswith("|") else format_concepts_field(iter_concept_ids(rc))  # pragma: no cover
            else:
                concepts = extract_concepts(text, domain, concept_registry)
            meta["concepts"] = concepts
            for c in iter_concept_ids(concepts):
                concepts_found[c] += 1  # pragma: no cover
            if (
                getattr(args, "enrich_metadata", False)
                and not args.dry_run
                and meta.get("source_type") == "code"
            ):
                extra = _generate_llm_metadata(
                    text,
                    str(partial.get("chunk_name") or ""),
                    args.enrich_model,
                    timeout_sec=float(getattr(args, "enrich_timeout", 120.0)),
                )
                meta.update({k: v for k, v in extra.items() if v})
                now = time.monotonic()
                if now >= _enrich_hb_next:
                    tail = abs_src if len(abs_src) <= 72 else "…" + abs_src[-70:]
                    print(
                        f"[ingest] LLM enrich progress: file {files_processed + 1}/{len(files_to_process)} "
                        f"chunk {i + 1}/{len(pieces)} — {tail}",
                        flush=True,
                    )
                    _enrich_hb_next = now + _enrich_hb_sec
            meta = finalize_metadata(meta)
            cn = str(meta.get("chunk_name") or "").strip()
            if cn:
                vocab_tokens.add(cn)
            df = str(meta.get("device_family") or "").strip()
            if df:
                vocab_tokens.add(df)
            rp = str(meta.get("relative_path") or "").strip()
            if rp:
                prp = Path(rp.replace("\\", "/"))
                vocab_tokens.add(prp.name)
                if prp.suffix:
                    vocab_tokens.add(prp.stem)
            try:
                cidx = int(meta.get("chunk_index") or i)
            except ValueError:  # pragma: no cover
                cidx = i  # pragma: no cover
            cid = make_chunk_id(abs_src, cidx, text)
            work_items.append((cid, text, meta))

        files_processed += 1
        if source_type == "code" and not extra.get("virtual"):
            repo_file_counts[repo] += 1
        if not args.dry_run:
            if extra.get("virtual"):
                file_hashes[src_key] = h
            else:
                file_hashes[abs_src] = h

    vocab_tokens.update(concepts_found.keys())
    vocab_path = db_path / "symbols_vocabulary.json"
    try:
        existing: List[Any] = []
        if vocab_path.is_file():
            try:
                existing = json.loads(vocab_path.read_text(encoding="utf-8", errors="replace"))
            except Exception:
                existing = []
        if not isinstance(existing, list):
            existing = []
        merged = sorted(
            {str(x).strip() for x in existing if str(x).strip()} | vocab_tokens
        )
        vocab_path.write_text(json.dumps(merged, indent=2), encoding="utf-8")
        logger.info("symbols_vocabulary written: %d tokens -> %s", len(merged), vocab_path)
    except Exception as exc:
        logger.warning("symbols_vocabulary write failed: %s", exc)

    if args.dry_run:
        logger.info("dry-run: %d files, %d chunks (planned)", files_processed, len(work_items))
        return 0

    chunk_q: "queue.Queue[Optional[List[Tuple[str, str, Dict[str, str]]]]]" = queue.Queue(maxsize=256)
    result_q: "queue.Queue[Optional[Tuple[List[str], List[str], List[Dict[str, str]], List[List[float]]]]]" = (
        queue.Queue(maxsize=512)
    )
    def writer_loop():
        while True:
            item = result_q.get()
            if item is WRITER_STOP:
                break
            if item is None:
                results_holder["failed"] += 1  # pragma: no cover
                continue  # pragma: no cover
            ids, texts, metas, embeddings = item
            try:
                existing_ids: set = set()
                try:
                    prev = coll.get(ids=ids, include=[])
                    if prev and prev.get("ids"):
                        existing_ids = set(prev["ids"])  # pragma: no cover
                except Exception:  # pragma: no cover
                    pass  # pragma: no cover
                created = sum(1 for i in ids if i not in existing_ids)
                updated = len(ids) - created
                results_holder["chunks_created"] += created
                results_holder["chunks_updated"] += updated
                coll.upsert(ids=ids, documents=texts, metadatas=metas, embeddings=embeddings)
                results_holder["processed"] += len(ids)
            except Exception as exc:  # pragma: no cover
                logger.exception("upsert failed: %s", exc)  # pragma: no cover
                results_holder["failed"] += len(ids)  # pragma: no cover
                results_holder["errors"].append(str(exc))  # pragma: no cover

    wthread = threading.Thread(target=writer_loop, daemon=True)
    wthread.start()

    batch_size, workers_n, embed_concurrency = resolve_embed_ingest_settings()
    batches = [work_items[i : i + batch_size] for i in range(0, len(work_items), batch_size)]
    use_async_embed = (
        os.environ.get("EMBED_ASYNC", "1").strip().lower() not in ("0", "false", "no")
        and aiohttp is not None
    )

    if use_async_embed:
        try:
            logger.info(
                "Starting async embedding: %d chunks in %d batch(es), concurrency=%d, model=%s "
                "(progress updates may be slow in the dashboard — this step is network-bound to Ollama)",
                len(work_items),
                len(batches),
                embed_concurrency,
                embed_model,
            )
            outs = asyncio.run(
                run_async_embedding_batches(batches, embed_model, embed_concurrency)
            )
        except Exception as exc:  # pragma: no cover
            logger.exception("async embedding failed: %s", exc)
            results_holder["errors"].append(str(exc))
            outs = [None] * len(batches)
        for bi, item in enumerate(outs):
            if item is None:
                results_holder["failed"] += len(batches[bi]) if bi < len(batches) else 0
            else:
                result_q.put(item)
    else:
        threads: List[threading.Thread] = []
        for wid in range(workers_n):
            t = threading.Thread(
                target=embedding_worker,
                args=(embed_model, wid, chunk_q, result_q),
                name=f"embed-{wid}",
                daemon=True,
            )
            t.start()
            threads.append(t)
        try:
            for batch in _tqdm_ingest(batches, desc="Embedding", unit="batch", total=len(batches)):
                if shutdown_event.is_set():
                    break  # pragma: no cover
                chunk_q.put(batch)
        finally:
            for _ in threads:
                chunk_q.put(None)
        for t in threads:
            t.join(timeout=600)

    result_q.put(WRITER_STOP)
    print(
        "[ingest] Waiting for Chroma writer / checkpoint (no tqdm here — safe after Embedding 100%)…",
        flush=True,
    )
    wthread.join(timeout=600)

    checkpoint[cp_key] = json.dumps(file_hashes)
    if new_git_head_commit:
        checkpoint[git_head_key] = new_git_head_commit
    save_checkpoint(db_path, checkpoint)
    if repo_file_counts:
        update_repos_manifest(db_path, collection_name, dict(repo_file_counts))

    duration = time.time() - t0
    record = {
        "ingestion_id": datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6],
        "mode": args.mode,
        "domain": domain,
        "collection": collection_name,
        "timestamp": ingestion_ts,
        "files_processed": files_processed,
        "chunks_created": results_holder["chunks_created"],
        "chunks_updated": results_holder["chunks_updated"],
        "chunks_upserted": results_holder["processed"],
        "chunks_deleted_stale": chunks_deleted,
        "concepts_found": sorted(concepts_found.keys()),
        "content_type_distribution": dict(ctype_dist),
        "embedding_model": embed_model,
        "duration_seconds": round(duration, 3),
        "errors": results_holder["errors"],
    }
    append_manifest(db_path, record)
    logger.info("Done: %s", record)
    return 0 if not results_holder["errors"] else 1


def _embed_documents_with_optional_timeout(
    embedder: OllamaEmbeddings, texts: List[str], timeout_sec: Optional[float]
) -> List[List[float]]:
    if not timeout_sec or timeout_sec <= 0:
        return embedder.embed_documents(texts)
    with ThreadPoolExecutor(max_workers=1) as pool:
        fut = pool.submit(embedder.embed_documents, texts)
        try:
            return fut.result(timeout=timeout_sec)
        except FuturesTimeoutError as exc:
            raise RuntimeError(f"Ollama embedding timed out after {timeout_sec}s") from exc


def feed_domain_document(
    filepath: str,
    domain: str,
    db_path: str,
    embed_model: str,
    concept_registry_path: Optional[str] = None,
    *,
    source_type: str = "auto",
    chroma_client: Optional[Any] = None,
    embedder: Optional[OllamaEmbeddings] = None,
    use_embed_lock: bool = True,
    embed_batch_timeout: Optional[float] = None,
    embed_lock_acquire_timeout: float = 300.0,
) -> Dict[str, Any]:
    """In-process single-file domain ingest (for MCP). Returns structured stats.

    When *chroma_client* / *embedder* are provided (e.g. MCP server), reuse them to avoid
    extra SQLite handles and embedder instances. Set *use_embed_lock* False when an outer
    layer already serializes embedding (e.g. asyncio.Semaphore).

    *source_type*: ``auto`` (default) detects ``rfc<number>.txt`` and uses ``chunk_rfc``;
    ``rfc`` forces RFC chunking; ``domain_doc`` forces markdown-domain chunking.
    """
    path = Path(filepath).resolve()
    text = path.read_text(encoding="utf-8", errors="replace")
    st = (source_type or "auto").strip().lower()
    if st not in ("auto", "rfc", "domain_doc"):
        st = "auto"
    if st == "rfc":
        use_rfc_chunker = True  # pragma: no cover
    elif st == "domain_doc":
        use_rfc_chunker = False
    else:
        use_rfc_chunker = _is_rfc_file(path)
    if use_rfc_chunker:
        parts = chunk_rfc(text, str(path), embed_model=embed_model)
        effective_source_type = "rfc"
        coll_mode = "rfc"
    else:
        parts = chunk_markdown_domain(text, str(path), embed_model=embed_model)
        effective_source_type = "domain_doc"
        coll_mode = "domain"
    reg = load_concept_registry(
        Path(concept_registry_path) if concept_registry_path else SCRIPT_DIR / "concept_registry.json"
    )
    dom = domain or "nms"
    concepts_all: set = set()
    sections: set = set()
    abs_src = str(path)
    coll_name = resolve_collection(coll_mode, dom, None)
    dbp = Path(db_path).resolve()
    dbp.mkdir(parents=True, exist_ok=True)
    client = chroma_client or chromadb.PersistentClient(path=str(dbp))
    coll = client.get_or_create_collection(name=coll_name)
    try:
        coll.delete(where={"source": abs_src})
    except Exception:  # pragma: no cover
        pass  # pragma: no cover
    embedder = embedder or OllamaEmbeddings(model=embed_model)
    dim_err = validate_embedding_dimension(coll, embedder, coll_name, embed_model)
    if dim_err:
        raise RuntimeError(dim_err)
    ingestion_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    work: List[Tuple[str, str, Dict[str, str]]] = []
    for i, (chunk_text, partial) in enumerate(parts):
        sections.add(
            str(partial.get("section") or partial.get("section_number") or "")
        )
        ctype = partial.get("content_type") or detect_content_type(chunk_text)
        raw_c = partial.get("concepts")
        if raw_c is not None and str(raw_c).strip() != "":
            rc = str(raw_c).strip()  # pragma: no cover
            concepts = rc if rc.startswith("|") else format_concepts_field(iter_concept_ids(rc))  # pragma: no cover
        else:
            concepts = extract_concepts(chunk_text, dom, reg)
        for c in iter_concept_ids(concepts):
            concepts_all.add(c)  # pragma: no cover
        base = empty_metadata()
        base.update(
            {
                "source": abs_src,
                "source_type": effective_source_type,
                "domain": dom,
                "repository": "feed",
                "relative_path": path.name,
                "extension": path.suffix.lower(),
                "file_size_kb": str(round(path.stat().st_size / 1024.0, 3)),
                "last_modified": datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                ),
                "ingestion_date": ingestion_ts,
                "ingestion_version": INGESTION_VERSION,
                "content_type": ctype,
                "concepts": concepts,
            }
        )
        meta = finalize_metadata({**base, **partial})
        try:
            cidx = int(meta.get("chunk_index") or i)
        except ValueError:
            cidx = i
        cid = make_chunk_id(abs_src, cidx, chunk_text)
        work.append((cid, chunk_text, meta))
    bs = 8
    for j in range(0, len(work), bs):
        batch = work[j : j + bs]
        ids = [x[0] for x in batch]
        texts = [x[1] for x in batch]
        metas = [x[2] for x in batch]

        def _do_embed() -> List[List[float]]:
            return _embed_documents_with_optional_timeout(embedder, texts, embed_batch_timeout)

        if use_embed_lock:
            acquired = _embed_lock.acquire(timeout=embed_lock_acquire_timeout)
            if not acquired:
                raise RuntimeError(
                    "Could not acquire embedding lock within "
                    f"{embed_lock_acquire_timeout}s; another ingest may be stuck."
                )
            try:
                embs = _do_embed()
            finally:
                _embed_lock.release()
        else:
            embs = _do_embed()
        coll.upsert(ids=ids, documents=texts, metadatas=metas, embeddings=embs)
    write_ingestion_config(dbp, embed_model)
    return {
        "chunk_count": len(parts),
        "sections_found": len([s for s in sections if s]),
        "concepts_found": sorted(concepts_all),
        "collection": coll_name,
        "source": abs_src,
    }


if __name__ == "__main__":
    raise SystemExit(main())
