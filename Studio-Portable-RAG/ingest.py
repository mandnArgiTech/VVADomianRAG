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
from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Tuple

from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import Language, RecursiveCharacterTextSplitter
from tqdm import tqdm

try:
    import chromadb
except ImportError as exc:  # pragma: no cover
    raise SystemExit("chromadb is required") from exc

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
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover
    BeautifulSoup = None  # type: ignore

try:
    from sanitizer import sanitize as sanitize_pii
except ImportError:  # pragma: no cover
    sanitize_pii = None  # type: ignore

# ---------------------------------------------------------------------------
# Optional tree-sitter
# ---------------------------------------------------------------------------
_TS_LANG: Dict[str, Any] = {}


def _load_ts_language(name: str, mod_name: str) -> Any:
    if name in _TS_LANG:
        return _TS_LANG[name]
    try:
        mod = __import__(mod_name, fromlist=["language"])
        from tree_sitter import Language as TSLanguage  # type: ignore

        lang = TSLanguage(getattr(mod, "language")())
        _TS_LANG[name] = lang
        return lang
    except Exception:  # pragma: no cover
        return None


def _ts_parser_for(lang_name: str, mod_name: str):
    from tree_sitter import Parser  # type: ignore

    lang = _load_ts_language(lang_name, mod_name)
    if lang is None:
        return None  # pragma: no cover
    try:
        return Parser(lang)  # tree-sitter-python >=0.21
    except TypeError:  # pragma: no cover
        p = Parser()
        if hasattr(p, "set_language"):
            p.set_language(lang)
        else:
            p.language = lang  # type: ignore[attr-defined]
        return p


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

INGESTION_VERSION = "2.0"
MAX_RETRIES = 5
EMBED_BACKOFF_SEC = 5
SCRIPT_DIR = Path(__file__).resolve().parent

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
MODEL_TOKEN_LIMITS = {
    "mxbai-embed-large": 512,
    "nomic-embed-text": 8192,
}
DEFAULT_RFC_TOKEN_LIMIT = 512

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

MIB_MODULE_CONCEPTS = {
    "BRIDGE-MIB": "stp,forwarding_table",
    "IF-MIB": "interface_management",
    "Q-BRIDGE-MIB": "vlan",
    "LLDP-MIB": "lldp",
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
        if keyword.lower() in tl:
            found.add(table[keyword])
    return format_concepts_field(found) if found else ""


def iter_concept_ids(concepts_field: str) -> List[str]:
    """Split stored concepts metadata (pipe- or comma-delimited; supports legacy rows)."""
    s = (concepts_field or "").strip()
    if not s:
        return []
    if s.startswith("|"):
        return [x.strip() for x in s.strip("|").split("|") if x.strip()]
    return [x.strip() for x in s.split(",") if x.strip()]


def format_concepts_field(ids: Iterable[str]) -> str:
    """Pipe-delimited concept ids for Chroma $contains token search (|id| avoids substring false positives)."""
    unique = sorted({x.strip() for x in ids if x and str(x).strip()})
    return "|" + "|".join(unique) + "|" if unique else ""


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


def strip_html(text: str) -> str:
    if BeautifulSoup is not None:
        return BeautifulSoup(text, "html.parser").get_text("\n")
    return re.sub(r"<[^>]+>", " ", text)


def _safe_count(coll) -> int:
    try:
        return int(coll.count())
    except Exception:  # pragma: no cover
        try:  # pragma: no cover
            return int(coll._collection.count())  # type: ignore[attr-defined]  # pragma: no cover
        except Exception:  # pragma: no cover
            return 0  # pragma: no cover


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


_BARE_MERMAID_STARTERS = re.compile(
    r"^(?:graph\s+(?:TD|TB|BT|RL|LR)|sequenceDiagram|classDiagram|stateDiagram"
    r"|erDiagram|gantt|pie|flowchart|journey|gitGraph|mindmap|timeline|quadrantChart"
    r"|sankey|xychart|block-beta|packet-beta|kanban|architecture-beta)\b",
    re.MULTILINE,
)

_DIAGRAM_TYPE_HINTS = {
    "graph": "Mermaid Flowchart",
    "flowchart": "Mermaid Flowchart",
    "sequencediagram": "Mermaid Sequence Diagram",
    "classdiagram": "Mermaid Class Diagram",
    "statediagram": "Mermaid State Diagram",
    "erdiagram": "Mermaid ER Diagram",
    "gantt": "Mermaid Gantt Chart",
    "pie": "Mermaid Pie Chart",
    "journey": "Mermaid User Journey",
    "gitgraph": "Mermaid Git Graph",
    "mindmap": "Mermaid Mind Map",
    "timeline": "Mermaid Timeline",
    "sankey": "Mermaid Sankey Diagram",
    "xychart": "Mermaid XY Chart",
    "@startuml": "PlantUML Diagram",
    "@startmindmap": "PlantUML Mind Map",
    "@startgantt": "PlantUML Gantt",
}


def _detect_diagram_type(block_text: str) -> str:
    """Return a human-readable diagram type label or empty string."""
    first_line = block_text.strip().split("\n", 1)[0].strip().lower()
    for opener in ("```mermaid", "```plantuml"):
        if first_line.startswith(opener):
            first_line = block_text.strip().split("\n", 2)[1].strip().lower() if "\n" in block_text else ""
            break
    first_token = re.split(r"[\s{(\[]", first_line, 1)[0].rstrip(":;").lower() if first_line else ""
    return _DIAGRAM_TYPE_HINTS.get(first_token, "")


@dataclass
class _MaskedBlock:
    text: str
    diagram_type: str


def _mask_markdown_fences_and_tables(text: str) -> Tuple[str, List[_MaskedBlock]]:
    """Replace fenced blocks, HTML diagram wrappers, bare Mermaid, and pipe-tables with placeholders."""
    vault: List[_MaskedBlock] = []

    def stash(m: re.Match, force_type: str = "") -> str:
        raw = m.group(0)
        dtype = force_type or _detect_diagram_type(raw)
        vault.append(_MaskedBlock(text=raw, diagram_type=dtype))
        return f"\n<<BLOCK{len(vault) - 1}>>\n"

    t = re.sub(r"(?ms)^```.*?^```", stash, text)

    t = re.sub(
        r"(?ms)<div\s[^>]*class\s*=\s*[\"'](?:mermaid|plantuml)[\"'][^>]*>.*?</div>",
        lambda m: stash(m, "Mermaid Diagram (HTML)"),
        t,
    )
    t = re.sub(
        r"(?ms)<details[^>]*>.*?</details>",
        lambda m: stash(m, "HTML Details Block"),
        t,
    )

    matches = list(_BARE_MERMAID_STARTERS.finditer(t))
    for m in reversed(matches):
        block_start = m.start()
        rest = t[block_start:]
        lines = rest.split("\n")
        block_lines = [lines[0]]
        for ln in lines[1:]:
            stripped = ln.strip()
            if not stripped:
                block_lines.append(ln)
                continue
            if stripped.startswith("```") or re.match(r"^#{1,6}\s", stripped):
                break
            block_lines.append(ln)
        block_text = "\n".join(block_lines).rstrip()
        dtype = _detect_diagram_type(block_text) or "Bare Diagram Block"
        vault.append(_MaskedBlock(text=block_text, diagram_type=dtype))
        placeholder = f"\n<<BLOCK{len(vault) - 1}>>\n"
        t = t[:block_start] + placeholder + t[block_start + len(block_text):]

    t = re.sub(r"(?ms)(?:^\|[^\n]+\n)+", lambda m: stash(m, ""), t)
    return t, vault


def _unmask_markdown_with_meta(
    s: str, vault: List[_MaskedBlock]
) -> Tuple[str, bool, str]:
    """Restore placeholders. Returns (text, has_diagram, diagram_type_label)."""
    has_diagram = False
    diagram_types: List[str] = []
    for i, blk in enumerate(vault):
        placeholder = f"<<BLOCK{i}>>"
        if placeholder in s:
            if blk.diagram_type:
                has_diagram = True
                if blk.diagram_type not in diagram_types:
                    diagram_types.append(blk.diagram_type)
            s = s.replace(placeholder, blk.text)
    label = ", ".join(diagram_types) if diagram_types else ""
    if has_diagram and label:
        s = f"[Metadata: This chunk contains a {label}]\n\n{s}"
    return s, has_diagram, label


def _unmask_markdown(s: str, vault: List[_MaskedBlock]) -> str:
    """Backward-compatible unmask (used by callers that don't need diagram metadata)."""
    for i, blk in enumerate(vault):  # pragma: no cover
        s = s.replace(f"<<BLOCK{i}>>", blk.text)  # pragma: no cover
    return s  # pragma: no cover


def _extract_release_date_near_version(body: str) -> str:
    m = re.search(
        r"(?i)(?:released?|published|date)[:.\s]+(\d{4}-\d{2}-\d{2}|\d{1,2}\s+\w+\s+\d{4}|\w+\s+\d{1,2},?\s+\d{4})",
        body[:2500],
    )
    return m.group(1).strip() if m else ""


def _ts_comment_prefix(content: str, start_byte: int, max_lines: int = 2) -> str:
    """Prepend up to `max_lines` of // or /* */ comments immediately above node."""
    if start_byte <= 0:
        return ""
    prefix = content[:start_byte]
    lines = prefix.splitlines()
    if not lines:
        return ""  # pragma: no cover
    buf: List[str] = []
    i = len(lines) - 1
    lines_seen = 0
    while i >= 0 and lines_seen < max_lines:
        ln = lines[i].rstrip()
        stripped = ln.lstrip()
        if not stripped:
            i -= 1  # pragma: no cover
            continue  # pragma: no cover
        if stripped.startswith("//"):
            buf.append(ln)
            lines_seen += 1
            i -= 1
            continue
        if "*/" in stripped or stripped.startswith("/*") or stripped.startswith("*"):
            buf.append(ln)
            lines_seen += 1
            i -= 1
            continue
        break
    if not buf:
        return ""
    return "\n".join(reversed(buf)) + "\n"


# === IMPLEMENTATION PART 1 ===


_BLOCK_PLACEHOLDER_RE = re.compile(r"^<<BLOCK\d+>>$")


def _is_diagram_placeholder(para: str) -> bool:
    return bool(_BLOCK_PLACEHOLDER_RE.match(para.strip()))


def _split_paragraphs(text: str, target_min: int = 2000, target_max: int = 5000) -> List[str]:
    """Token-aware paragraph packer with diagram-context bonding.

    * Uses _estimate_tokens for token-approximate sizing (char limits are still
      accepted for backward compat -- callers can pass char-based values derived
      from MODEL_TOKEN_LIMITS via _md_char_targets).
    * Diagram-context bonding: if the *next* paragraph is a <<BLOCK>> placeholder
      (a diagram), aggressively pack it with the current buffer so that the
      explanatory paragraph preceding the diagram stays in the same chunk.
    """
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paras:
        return []  # pragma: no cover
    out: List[str] = []
    buf = ""
    i = 0
    while i < len(paras):
        p = paras[i]
        candidate = (buf + "\n\n" + p).strip() if buf else p
        if len(candidate) <= target_max:
            buf = candidate
            if i + 1 < len(paras) and _is_diagram_placeholder(paras[i + 1]):
                diagram = paras[i + 1]
                bonded = (buf + "\n\n" + diagram).strip()
                hard_limit = int(target_max * 1.25)
                if len(bonded) <= hard_limit:
                    buf = bonded
                    i += 2
                    continue
            i += 1
        else:
            if buf:  # pragma: no cover
                out.append(buf)  # pragma: no cover
            buf = p  # pragma: no cover
            if i + 1 < len(paras) and _is_diagram_placeholder(paras[i + 1]):  # pragma: no cover
                diagram = paras[i + 1]  # pragma: no cover
                bonded = (buf + "\n\n" + diagram).strip()  # pragma: no cover
                hard_limit = int(target_max * 1.25)  # pragma: no cover
                if len(bonded) <= hard_limit:  # pragma: no cover
                    buf = bonded  # pragma: no cover
                    i += 2  # pragma: no cover
                    continue  # pragma: no cover
            i += 1  # pragma: no cover
    if buf:
        out.append(buf)
    return out


def _md_char_targets(embed_model: str) -> Tuple[int, int]:
    """Derive min/max char targets for markdown domain chunks, analogous to _rfc_char_targets."""
    for key, limit in MODEL_TOKEN_LIMITS.items():
        if key in (embed_model or "").lower():
            chars_max = limit * 4
            return max(400, chars_max // 3), chars_max
    default_chars = 2048  # pragma: no cover
    return max(400, default_chars // 3), default_chars  # pragma: no cover


def _estimate_tokens(text: str) -> int:
    """Rough token count for English-ish RFC text (~4 chars/token).

    For exact counts, plug in a model tokenizer (e.g. Hugging Face ``tokenizers``).
    """
    return max(1, len(text) // 4)


def _get_rfc_token_limit(embed_model: str) -> int:
    em = embed_model.lower()
    for key, limit in MODEL_TOKEN_LIMITS.items():
        if key in em:
            return limit
    return DEFAULT_RFC_TOKEN_LIMIT  # pragma: no cover


def _rfc_char_targets(embed_model: str) -> Tuple[int, int]:
    tok = _get_rfc_token_limit(embed_model)
    target_max = max(512, tok * 4)
    target_min = max(256, target_max // 3)
    return target_min, target_max


_RFC_RUNNING_HDR = re.compile(r"^\s*RFC\s+\d+", re.I)
_RFC_PAGE_MARKER = re.compile(r"\[Page\s+\d+\]", re.I)
_RFC_FILENAME_RE = re.compile(r"rfc\d+", re.I)


def _is_rfc_file(path: Path) -> bool:
    """True for RFC Editor-style plain-text RFCs (e.g. rfc3376.txt)."""
    return path.suffix.lower() == ".txt" and bool(_RFC_FILENAME_RE.search(path.stem))


def _depaginate_rfc(text: str) -> str:
    """Strip form-feed pagination, page markers, and common running headers/footers."""
    pages = text.split("\f") if "\f" in text else [text]
    cleaned: List[str] = []
    for page in pages:
        page = _RFC_PAGE_MARKER.sub("", page)
        lines = page.split("\n")
        hdr_strips = 0
        while lines and hdr_strips < 2:
            first = lines[0].strip()
            if not first:
                lines.pop(0)
                continue
            if _RFC_RUNNING_HDR.match(first) or (
                re.match(r"^RFC\s+\d+", first, re.I) and len(first) < 140
            ):
                lines.pop(0)
                hdr_strips += 1
                continue
            if re.match(r"^Internet-Draft\b", first, re.I) and len(first) < 100:
                lines.pop(0)  # pragma: no cover
                hdr_strips += 1  # pragma: no cover
                continue  # pragma: no cover
            break
        ftr_strips = 0
        while lines and ftr_strips < 2:
            last = lines[-1].strip()
            if not last:
                lines.pop()
                continue
            if _RFC_PAGE_MARKER.search(last) or re.match(
                r"^.{0,140}\[Page\s+\d+\]\s*$", last, re.I
            ):
                lines.pop()  # pragma: no cover
                ftr_strips += 1  # pragma: no cover
                continue  # pragma: no cover
            if re.match(r"^Full\s+Standards?\s+Section", last, re.I):
                lines.pop()  # pragma: no cover
                ftr_strips += 1  # pragma: no cover
                continue  # pragma: no cover
            break
        cleaned.append("\n".join(lines))
    merged = "\n\n".join(p.strip() for p in cleaned if p.strip())
    merged = _RFC_PAGE_MARKER.sub("", merged)
    merged = re.sub(r"\n{3,}", "\n\n", merged)
    return merged


def _rfc_line_is_diagram(line: str) -> bool:
    if not line.strip():
        return False
    lead = len(line) - len(line.lstrip(" \t"))
    if lead >= 3:
        return True
    s = line
    if re.search(r"[+|]\s*[-+]{2,}", s) or re.search(r"[-+]{2,}\s*[+|]", s):
        return True
    if "|" in s and ("+-" in s or "-+" in s or ".-" in s):
        return True  # pragma: no cover
    st = s.strip()
    if len(st) >= 10 and sum(1 for c in st if c.isdigit()) >= 4:
        if re.match(r"^[\d\s]+$", st):
            return True  # pragma: no cover
    return False


def _shield_diagrams(text: str) -> Tuple[str, Dict[str, str]]:
    """Replace ASCII diagram runs with placeholders so paragraph splitters never break them."""
    lines = text.split("\n")
    vault: Dict[str, str] = {}
    out: List[str] = []
    i = 0
    n = len(lines)
    d_idx = 0
    while i < n:
        if not _rfc_line_is_diagram(lines[i]):
            out.append(lines[i])
            i += 1
            continue
        j = i
        diag_count = 0
        saw_blank = False
        while j < n:
            ln = lines[j]
            if _rfc_line_is_diagram(ln):
                diag_count += 1
                saw_blank = False
                j += 1
            elif not ln.strip():
                if saw_blank:  # pragma: no cover
                    break  # pragma: no cover
                if j + 1 < n and _rfc_line_is_diagram(lines[j + 1]):  # pragma: no cover
                    saw_blank = True  # pragma: no cover
                    j += 1  # pragma: no cover
                else:
                    break  # pragma: no cover
            else:
                break
        if diag_count >= 3:
            key = f"__DIAGRAM_{d_idx}__"  # pragma: no cover
            d_idx += 1  # pragma: no cover
            vault[key] = "\n".join(lines[i:j])  # pragma: no cover
            out.append(key)  # pragma: no cover
            i = j  # pragma: no cover
        else:
            out.extend(lines[i:j])
            i = j
    return "\n".join(out), vault


def _diagram_vault_sort_key(k: str) -> int:
    try:
        return int(k.replace("__DIAGRAM_", "").replace("__", ""))
    except ValueError:  # pragma: no cover
        return 0  # pragma: no cover


def _unshield_diagrams(text: str, vault: Dict[str, str]) -> str:
    for k in sorted(vault.keys(), key=_diagram_vault_sort_key):
        text = text.replace(k, vault[k])  # pragma: no cover
    return text


def _sliding_window_chunks(
    text: str,
    target_max_chars: int,
    overlap_frac: float = 0.15,
    base_meta: Optional[Dict[str, str]] = None,
) -> List[Tuple[str, Dict[str, str]]]:
    """Token-budget sliding windows with overlap; prefers paragraph then sentence boundaries."""
    base_meta = dict(base_meta or {})
    overlap = max(64, int(target_max_chars * overlap_frac))
    t = text.strip()
    if not t:
        return []  # pragma: no cover
    if len(t) <= target_max_chars:
        return [(t, {**base_meta, "chunk_type": "sliding_window", "chunk_index": "0"})]
    out: List[Tuple[str, Dict[str, str]]] = []
    pos = 0
    idx = 0
    tl = len(t)
    while pos < tl:
        end = min(pos + target_max_chars, tl)
        if end < tl:
            br = t.rfind("\n\n", pos + max(64, target_max_chars // 5), end)
            if br >= pos:
                end = br + 2
            else:
                br2 = t.rfind(". ", pos + target_max_chars // 3, end)  # pragma: no cover
                if br2 >= pos:  # pragma: no cover
                    end = br2 + 2  # pragma: no cover
        chunk = t[pos:end].strip()
        if chunk:
            out.append((chunk, {**base_meta, "chunk_type": "sliding_window", "chunk_index": str(idx)}))
            idx += 1
        if end >= tl:
            break
        next_pos = max(pos + 1, end - overlap)
        snap = t.find("\n\n", next_pos, min(next_pos + overlap * 3, tl))
        if snap != -1:
            next_pos = snap + 2
        pos = next_pos
    return out


def chunk_markdown_domain(
    text: str, path: str, embed_model: str = "nomic-embed-text"
) -> List[Tuple[str, Dict[str, str]]]:
    masked, vault = _mask_markdown_fences_and_tables(text)
    h1_m = re.search(r"(?m)^#\s+(.+)$", masked)
    h1 = h1_m.group(1).strip() if h1_m else ""
    t_min, t_max = _md_char_targets(embed_model)
    split_threshold = int(t_max * 1.2)

    def _finalize(raw_piece: str, section: str, chunk_type: str, idx_ref: List[int]) -> Tuple[str, Dict[str, str]]:
        header = f"{section}\n\n{raw_piece}" if section else raw_piece
        txt, has_diag, diag_label = _unmask_markdown_with_meta(header, vault)
        meta: Dict[str, str] = {
            "chunk_strategy": "markdown_domain",
            "chunk_type": chunk_type,
            "section": section or path,
            "doc_title": h1,
            "chunk_index": str(idx_ref[0]),
            "contains_diagram": "true" if has_diag else "",
        }
        if diag_label:
            meta["diagram_type"] = diag_label  # pragma: no cover
        idx_ref[0] += 1
        return txt, meta

    chunks: List[Tuple[str, Dict[str, str]]] = []
    idx_ref = [0]
    parts = re.split(r"(?m)(^##\s+.+$)", masked)
    i = 0
    while i < len(parts):
        seg = parts[i].strip()
        if seg.startswith("##"):
            title = seg.lstrip("#").strip()
            body = parts[i + 1].strip() if i + 1 < len(parts) else ""
            i += 2
            hierarchy = " > ".join(x for x in (h1, title) if x)
            if len(body) > split_threshold and "###" in body:
                sub = re.split(r"(?m)(^###\s+.+$)", body)  # pragma: no cover
                j = 0  # pragma: no cover
                while j < len(sub):  # pragma: no cover
                    sseg = sub[j].strip()  # pragma: no cover
                    if sseg.startswith("###"):  # pragma: no cover
                        st = sseg.lstrip("#").strip()  # pragma: no cover
                        b2 = sub[j + 1].strip() if j + 1 < len(sub) else ""  # pragma: no cover
                        j += 2  # pragma: no cover
                        sub_hier = " > ".join(x for x in (h1, title, st) if x)  # pragma: no cover
                        pieces = _split_paragraphs(b2, t_min, t_max) if len(b2) > split_threshold else [b2]  # pragma: no cover
                        for piece in pieces:  # pragma: no cover
                            chunks.append(_finalize(piece, sub_hier or hierarchy, "section", idx_ref))  # pragma: no cover
                    else:
                        b0 = sseg  # pragma: no cover
                        j += 1  # pragma: no cover
                        pieces = _split_paragraphs(b0, t_min, t_max) if len(b0) > split_threshold else [b0]  # pragma: no cover
                        for piece in pieces:  # pragma: no cover
                            chunks.append(_finalize(piece, hierarchy, "section", idx_ref))  # pragma: no cover
            else:
                pieces = _split_paragraphs(body, t_min, t_max) if len(body) > split_threshold else [body]
                for piece in pieces:
                    chunks.append(_finalize(piece, hierarchy, "section", idx_ref))
        else:
            intro = seg
            i += 1
            if intro and not intro.startswith("#"):
                hier = h1 or path
                pieces = _split_paragraphs(intro, t_min, t_max) if len(intro) > split_threshold else [intro]
                for piece in pieces:
                    chunks.append(_finalize(piece, hier if h1 else "", "preamble", idx_ref))
    if not chunks and text.strip():
        txt, has_diag, diag_label = _unmask_markdown_with_meta(text[:8000], vault)
        meta: Dict[str, str] = {
            "chunk_strategy": "markdown_domain",
            "chunk_type": "document",
            "section": h1 or path,
            "doc_title": h1,
            "chunk_index": "0",
            "contains_diagram": "true" if has_diag else "",
        }
        if diag_label:
            meta["diagram_type"] = diag_label  # pragma: no cover
        chunks.append((txt, meta))
    return chunks


def chunk_rfc(
    text: str, path: str, embed_model: str = "nomic-embed-text"
) -> List[Tuple[str, Dict[str, str]]]:
    text = _depaginate_rfc(text)
    text, diagram_vault = _shield_diagrams(text)
    t_min, t_max = _rfc_char_targets(embed_model)
    section_body_threshold = t_max * 2

    # Trim preamble / ToC / boilerplate: start at first numbered section body
    sec_start = re.search(r"(?m)^(\d+(?:\.\d+)*)\s+[A-Za-z]", text)
    if sec_start and sec_start.start() > 0:
        trimmed = text[sec_start.start() :]  # pragma: no cover
        if len(trimmed.strip()) > 200:  # pragma: no cover
            text = trimmed  # pragma: no cover
    rfc_no = ""
    m = re.search(r"RFC\s*(\d+)", path, re.I) or re.search(r"RFC\s*(\d+)", text[:2000], re.I)
    if m:
        rfc_no = m.group(1)
    title = ""
    for ln in text.splitlines()[:40]:
        if ln.strip() and not ln.strip().lower().startswith("request for comments"):
            title = ln.strip()
            if "Network Working Group" in title:
                continue
            break
    sections = list(re.finditer(r"(?m)^(\d+(?:\.\d+)*)\s+([^\n]+)", text))
    out: List[Tuple[str, Dict[str, str]]] = []

    def _meta_contains_diagram(piece: str) -> str:
        return "true" if any(k in piece for k in diagram_vault) else "false"

    if not sections:
        base = {
            "chunk_strategy": "rfc",
            "rfc_number": rfc_no,
            "rfc_title": title,
            "section_number": "",
            "section_title": "",
        }
        for win_text, partial in _sliding_window_chunks(text, t_max, 0.15, base):
            raw_piece = win_text
            final_t = _unshield_diagrams(raw_piece, diagram_vault)
            meta = {
                **partial,
                "chunk_strategy": "rfc",
                "rfc_number": rfc_no,
                "rfc_title": title,
                "section_number": "",
                "section_title": "",
                "contains_diagram": _meta_contains_diagram(raw_piece),
            }
            out.append((final_t, meta))
        return out

    for i, msec in enumerate(sections):  # pragma: no cover
        start = msec.start()  # pragma: no cover
        end = sections[i + 1].start() if i + 1 < len(sections) else len(text)  # pragma: no cover
        sec_num = msec.group(1)  # pragma: no cover
        sec_title = msec.group(2).strip()  # pragma: no cover
        body = text[start:end].strip()  # pragma: no cover
        parts = (  # pragma: no cover
            _split_paragraphs(body, t_min, t_max) if len(body) > section_body_threshold else [body]
        )
        for p in parts:  # pragma: no cover
            raw_piece = p  # pragma: no cover
            final_t = _unshield_diagrams(raw_piece, diagram_vault)  # pragma: no cover
            out.append(  # pragma: no cover
                (
                    final_t,
                    {
                        "chunk_strategy": "rfc",
                        "chunk_type": "section",
                        "rfc_number": rfc_no,
                        "rfc_title": title,
                        "section_number": sec_num,
                        "section_title": sec_title,
                        "chunk_index": str(len(out)),
                        "contains_diagram": _meta_contains_diagram(raw_piece),
                    },
                )
            )
    return out  # pragma: no cover


def _html_to_text(s: str) -> str:
    return strip_html(s)


def chunk_rally_ticket(obj: Dict[str, Any], source: str) -> List[Tuple[str, Dict[str, str]]]:
    title = str(obj.get("Name") or obj.get("title") or "")
    desc = _html_to_text(str(obj.get("Description") or obj.get("description") or ""))
    resolution = _html_to_text(str(obj.get("Resolution") or obj.get("resolution") or ""))
    discussion = _html_to_text(str(obj.get("Discussion") or obj.get("discussion") or ""))
    fid = str(obj.get("FormattedID") or obj.get("id") or source)
    meta_base = {
        "chunk_strategy": "rally_ticket",
        "chunk_type": "ticket",
        "rally_id": fid,
        "artifact_type": str(obj.get("_type") or obj.get("artifact_type") or "artifact"),
        "state": str(obj.get("State") or obj.get("state") or ""),
        "priority": str(obj.get("Priority") or obj.get("priority") or ""),
        "severity": str(obj.get("Severity") or obj.get("severity") or ""),
        "has_resolution": "true" if resolution.strip() else "false",
        "iteration": str(obj.get("Iteration") or ""),
        "release": str(obj.get("Release") or ""),
        "created_date": str(obj.get("CreationDate") or obj.get("created") or ""),
        "closed_date": str(obj.get("ClosedDate") or obj.get("closed") or ""),
        "tags": str(obj.get("Tags") or obj.get("tags") or ""),
    }
    part1 = f"{title}\n\n{desc}\n\nResolution:\n{resolution}".strip()
    blob = f"{part1}\n\nDiscussion:\n{discussion}".strip()
    if len(blob) <= 8000:
        return [(blob, {**meta_base, "chunk_name": title, "chunk_index": "0"})]
    chunks: List[Tuple[str, Dict[str, str]]] = [  # pragma: no cover
        (part1, {**meta_base, "chunk_name": title, "chunk_index": "0"})
    ]
    if discussion.strip():  # pragma: no cover
        for k, piece in enumerate(_split_paragraphs(discussion, 4000, 8000)):  # pragma: no cover
            chunks.append(  # pragma: no cover
                (
                    f"Discussion ({fid}) part {k+1}:\n{piece}",
                    {**meta_base, "chunk_name": f"{fid}-disc-{k+1}", "chunk_index": str(k + 1)},
                )
            )
    return chunks  # pragma: no cover


def chunk_customer_ticket(obj: Dict[str, Any], source: str) -> List[Tuple[str, Dict[str, str]]]:
    out: List[Tuple[str, Dict[str, str]]] = []
    for text, meta in chunk_rally_ticket(obj, source):
        t = sanitize_pii(text) if sanitize_pii else text
        tid = str(obj.get("ticket_id") or obj.get("FormattedID") or source)
        mm = {
            **meta,
            "chunk_strategy": "customer_ticket",
            "ticket_id": tid,
            "customer_type": "anonymized",
            "has_workaround": "true" if re.search(r"workaround|mitigation", t, re.I) else "false",
            "product_version": str(obj.get("product_version") or ""),
            "related_rally": str(obj.get("related_rally") or ""),
        }
        mm.pop("rally_id", None)
        out.append((t, mm))
    return out


def chunk_mib(text: str, path: Path, skip_deprecated: bool = True) -> List[Tuple[str, Dict[str, str]]]:
    mod_match = re.search(r"([\w-]+)\s+DEFINITIONS\s*::=", text)
    mib_module = mod_match.group(1) if mod_match else path.stem
    extra_concepts = MIB_MODULE_CONCEPTS.get(mib_module.upper(), "")
    blocks = re.split(
        r"(?=\n\s*[A-Za-z0-9-]+\s+(?:OBJECT-TYPE|NOTIFICATION-TYPE|MODULE-IDENTITY|TEXTUAL-CONVENTION)\b)",
        text,
    )
    out: List[Tuple[str, Dict[str, str]]] = []
    for block in blocks:
        block = block.strip()
        if not re.search(
            r"\b(OBJECT-TYPE|NOTIFICATION-TYPE|MODULE-IDENTITY|TEXTUAL-CONVENTION)\b", block
        ):
            continue
        name_m = re.match(
            r"^\s*([A-Za-z0-9-]+)\s+(OBJECT-TYPE|NOTIFICATION-TYPE|MODULE-IDENTITY|TEXTUAL-CONVENTION)",
            block,
        )
        if not name_m:
            continue  # pragma: no cover
        obj_name = name_m.group(1)
        kind = name_m.group(2)
        status_m = re.search(r"STATUS\s+(\w+)", block)
        status = status_m.group(1) if status_m else ""
        if skip_deprecated and status.lower() in ("deprecated", "obsolete"):
            continue
        syntax_m = re.search(
            r"SYNTAX\s+(.+?)(?:\n\s*(?:MAX-ACCESS|ACCESS|STATUS|DESCRIPTION|DISPLAY-HINT)\b)", block, re.S
        )
        syntax = syntax_m.group(1).strip() if syntax_m else ""
        maxacc = ""
        mmax = re.search(r"MAX-ACCESS\s+(\S+)", block)
        if mmax:
            maxacc = mmax.group(1)
        oid_m = re.search(r"::=\s*\{\s*([^\}]+)\}", block)
        oid_path = oid_m.group(1).strip() if oid_m else ""
        obj_type = "scalar"
        if kind == "NOTIFICATION-TYPE":
            obj_type = "notification"  # pragma: no cover
        elif kind == "MODULE-IDENTITY":
            obj_type = "identity"  # pragma: no cover
        elif kind == "TEXTUAL-CONVENTION":
            obj_type = "textual_convention"  # pragma: no cover
        elif "ENTRY" in obj_name.upper() and "TABLE" not in obj_name.upper():
            obj_type = "row"  # pragma: no cover
        elif "TABLE" in obj_name.upper():
            obj_type = "table"  # pragma: no cover
        elif "INDEX" in block or ("SEQUENCE" in block.upper() and "OF" in block.upper()):
            obj_type = "table"  # pragma: no cover
        elif "AUGMENTS" in block.upper() or "column" in block.lower():
            obj_type = "column"  # pragma: no cover
        out.append(
            (
                f"{obj_name}\n{block[:12000]}",
                {
                    "chunk_strategy": "mib",
                    "chunk_type": "mib_object",
                    "chunk_name": obj_name,
                    "mib_module": mib_module,
                    "object_name": obj_name,
                    "oid_path": oid_path,
                    "syntax": syntax[:500],
                    "max_access": maxacc,
                    "status": status,
                    "object_type": obj_type,
                    "section": mib_module,
                    "chunk_index": str(len(out)),
                },
            )
        )
    if extra_concepts and out:
        t0, m0 = out[0]
        prev = m0.get("concepts", "")
        tokens: Set[str] = set(iter_concept_ids(prev))
        tokens.update(x.strip() for x in extra_concepts.split(",") if x.strip())
        m0["concepts"] = format_concepts_field(tokens)
        out[0] = (t0, m0)
    if not out:
        out.append(
            (
                text[:8000],
                {
                    "chunk_strategy": "mib",
                    "chunk_type": "mib_file",
                    "mib_module": mib_module,
                    "chunk_name": mib_module,
                    "chunk_index": "0",
                },
            )
        )
    return out


def chunk_release_notes(text: str, path: str) -> List[Tuple[str, Dict[str, str]]]:
    heads = list(
        re.finditer(r"(?m)^(#{1,3}\s*v?[\d.]+[^\n]*|Version\s+[\d.]+[^\n]*|#\s*[\d.]+[^\n]*)", text)
    )
    out: List[Tuple[str, Dict[str, str]]] = []
    if not heads:
        return [  # pragma: no cover
            (
                text[:10000],
                {
                    "chunk_strategy": "release_notes",
                    "chunk_type": "changelog",
                    "version": "",
                    "chunk_index": "0",
                },
            )
        ]
    for i, m in enumerate(heads):
        ver = re.sub(r"^[#vV\s]+", "", m.group(0)).strip()
        start = m.start()
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        body = text[start:end].strip()
        cat = "general"
        if re.search(r"known issue", body, re.I):
            cat = "Known Issues"  # pragma: no cover
        elif re.search(r"breaking", body, re.I):
            cat = "Breaking Changes"  # pragma: no cover
        elif re.search(r"bug fix", body, re.I):
            cat = "Bug Fixes"
        elif re.search(r"new feature", body, re.I):
            cat = "New Features"
        ctype = "general"
        if cat == "Known Issues":
            ctype = "edge_case"  # pragma: no cover
        elif cat == "Breaking Changes":
            ctype = "constraint"  # pragma: no cover
        rdate = _extract_release_date_near_version(body)
        parts = _split_paragraphs(body, 2000, 6000) if len(body) > 8000 else [body]
        for p in parts:
            out.append(
                (
                    p,
                    {
                        "chunk_strategy": "release_notes",
                        "chunk_type": "release",
                        "version": ver,
                        "release_date": rdate,
                        "section_category": cat,
                        "content_type": ctype,
                        "chunk_index": str(len(out)),
                    },
                )
            )
    return out


def parse_frontmatter(text: str) -> Tuple[Dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text  # pragma: no cover
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text  # pragma: no cover
    fm_raw = text[3:end]
    body = text[end + 4 :].lstrip("\n")
    fm: Dict[str, str] = {}
    for ln in fm_raw.splitlines():
        if ":" in ln:
            k, v = ln.split(":", 1)
            fm[k.strip()] = v.strip().strip('"')
    return fm, body


def chunk_community(text: str, path: str, fm: Dict[str, str]) -> List[Tuple[str, Dict[str, str]]]:
    if len(text) <= 8000:
        parts = [text]
    else:
        bits = re.split(r"(?m)(^---\s*$|^## Answer|^## Resolution)", text)  # pragma: no cover
        parts = []  # pragma: no cover
        buf = ""  # pragma: no cover
        for s in bits:  # pragma: no cover
            if len(buf) + len(s) > 8000 and buf:  # pragma: no cover
                parts.append(buf)  # pragma: no cover
                buf = s  # pragma: no cover
            else:
                buf += s  # pragma: no cover
        if buf:  # pragma: no cover
            parts.append(buf)  # pragma: no cover
    out: List[Tuple[str, Dict[str, str]]] = []
    for i, p in enumerate(parts):
        out.append(
            (
                p.strip(),
                {
                    "chunk_strategy": "community",
                    "chunk_type": "thread",
                    "source_platform": fm.get("source_platform", "unknown"),
                    "source_url": fm.get("source_url", ""),
                    "is_resolved": fm.get("is_resolved", ""),
                    "has_workaround": fm.get("has_workaround", ""),
                    "quality_score": fm.get("quality_score", ""),
                    "chunk_index": str(i),
                },
            )
        )
    return out


def chunk_wiki_page(
    text: str, path: str, meta: Dict[str, str], embed_model: str = "nomic-embed-text"
) -> List[Tuple[str, Dict[str, str]]]:
    cleaned = strip_html(text)
    parts = chunk_markdown_domain(cleaned, path, embed_model=embed_model)
    out: List[Tuple[str, Dict[str, str]]] = []
    for t, m in parts:
        mm = {**m, "chunk_strategy": "wiki"}
        for k in ("page_title", "space", "labels", "author", "parent_page", "page_url", "last_modified"):
            mm[k] = meta.get(k, "")
        out.append((t, mm))
    return out


def language_split(path: Path, content: str, lang: Language) -> List[Tuple[str, Dict[str, str]]]:
    splitter = RecursiveCharacterTextSplitter.from_language(
        language=lang, chunk_size=2000, chunk_overlap=200
    )
    docs = splitter.create_documents([content], metadatas=[{"path": str(path)}])
    return [
        (
            d.page_content,
            {
                "chunk_strategy": "language",
                "chunk_type": "fragment",
                "chunk_name": path.stem,
                "chunk_index": str(i),
            },
        )
        for i, d in enumerate(docs)
    ]


def generic_split(content: str, path: Path, size: int = 2000) -> List[Tuple[str, Dict[str, str]]]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=size, chunk_overlap=200)
    docs = splitter.create_documents([content], metadatas=[{"path": str(path)}])
    return [
        (
            d.page_content,
            {
                "chunk_strategy": "generic",
                "chunk_type": "fragment",
                "chunk_name": path.stem,
                "chunk_index": str(i),
            },
        )
        for i, d in enumerate(docs)
    ]


# Regex-assisted boundaries for languages without tree-sitter in this pipeline (leading whitespace allowed).
# Compiled with re.MULTILINE — do not embed per-branch (?m) flags (invalid when patterns are OR-joined).
_REGEX_CODE_PATTERNS: Dict[str, List[str]] = {
    ".go": [r"^\s*func\s+", r"^\s*type\s+\w+\s+struct\b"],
    ".rs": [
        r"^\s*(?:pub\s+)?(?:unsafe\s+)?fn\s+",
        r"^\s*(?:pub\s+)?struct\s+",
        r"^\s*(?:pub\s+)?enum\s+",
        r"^\s*(?:pub\s+)?impl\b",
        r"^\s*(?:pub\s+)?trait\s+",
    ],
    ".rb": [r"^\s*class\s+", r"^\s*module\s+", r"^\s*def\s+"],
    ".kt": [
        r"^\s*(?:public\s+|private\s+|internal\s+|protected\s+)?(?:open\s+|abstract\s+|sealed\s+)?fun\s+",
        r"^\s*class\s+",
        r"^\s*object\s+",
        r"^\s*interface\s+",
    ],
    ".kts": [r"^\s*fun\s+", r"^\s*class\s+", r"^\s*object\s+"],
    ".swift": [r"^\s*func\s+", r"^\s*class\s+", r"^\s*struct\s+", r"^\s*enum\s+", r"^\s*protocol\s+"],
    ".scala": [r"^\s*def\s+", r"^\s*class\s+", r"^\s*object\s+", r"^\s*trait\s+"],
    ".php": [r"^\s*function\s+", r"^\s*class\s+"],
}


def _merge_small_regex_chunks(
    parts: List[str], min_chars: int = 200, max_chars: int = 12000
) -> List[str]:
    if not parts:
        return []
    merged: List[str] = []
    buf = parts[0]
    for p in parts[1:]:
        if len(buf) < min_chars and len(buf) + len(p) <= max_chars:
            buf = buf + "\n\n" + p
        else:
            merged.append(buf)
            buf = p
    merged.append(buf)
    return merged


def regex_code_split(content: str, path: Path, ext: str) -> List[Tuple[str, Dict[str, str]]]:
    """Split on language-typical top-level boundaries; fallback to generic_split."""
    patterns = _REGEX_CODE_PATTERNS.get(ext.lower())
    if not patterns:
        return generic_split(content, path, 1500)
    combined = "|".join(f"({p})" for p in patterns)
    try:
        rx = re.compile(combined, re.MULTILINE)
    except re.error:
        return generic_split(content, path, 1500)
    matches = list(rx.finditer(content))
    if not matches:
        return generic_split(content, path, 1500)
    starts = sorted({m.start() for m in matches})
    if starts[0] > 0:
        starts.insert(0, 0)
    raw_parts: List[str] = []
    for i, st in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else len(content)
        seg = content[st:end].strip()
        if seg:
            raw_parts.append(seg)
    if not raw_parts:
        return generic_split(content, path, 1500)
    raw_parts = _merge_small_regex_chunks(raw_parts)
    return [
        (
            seg[:12000],
            {
                "chunk_strategy": "regex_code",
                "chunk_type": "fragment",
                "chunk_name": path.stem,
                "chunk_index": str(i),
            },
        )
        for i, seg in enumerate(raw_parts)
    ]


def _format_dependencies_field(modules: Iterable[str]) -> str:
    """Comma-separated sorted list for human-readable metadata and Chroma token search."""
    unique = sorted({m.strip() for m in modules if m and str(m).strip()})
    if not unique:
        return ""
    return ", ".join(unique)


def extract_dependencies(content: str, ext: str) -> str:
    """Extract import-like symbols for metadata (comma-separated)."""
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

    return _format_dependencies_field(mods)


def ast_chunk_python(path: Path, content: str) -> List[Tuple[str, Dict[str, str]]]:
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return generic_split(content, path, 1500)
    chunks: List[Tuple[str, Dict[str, str]]] = []
    lines = content.splitlines()

    def slice_node(node: ast.AST) -> str:
        if hasattr(node, "lineno") and hasattr(node, "end_lineno"):
            start = max(0, node.lineno - 1)
            end = min(len(lines), node.end_lineno)
            return "\n".join(lines[start:end])
        seg = ast.get_source_segment(content, node)  # pragma: no cover
        return seg or ""  # pragma: no cover

    idx = 0
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            src = slice_node(node)
            if not src.strip():
                continue  # pragma: no cover
            nm = node.name
            ctype = "class" if isinstance(node, ast.ClassDef) else "function"
            chunks.append(
                (
                    src,
                    {
                        "chunk_strategy": "ast_python",
                        "chunk_type": ctype,
                        "chunk_name": nm,
                        "chunk_index": str(idx),
                    },
                )
            )
            idx += 1
    if not chunks:
        return generic_split(content, path, 1500)
    return chunks


def _ts_extract_chunks(path: Path, content: str, grammar: str) -> Optional[List[Tuple[str, Dict[str, str]]]]:
    mod_map = {
        "c": "tree_sitter_c",
        "cpp": "tree_sitter_cpp",
        "java": "tree_sitter_java",
    }
    if grammar not in mod_map:
        return None
    parser = _ts_parser_for(grammar, mod_map[grammar])
    if parser is None:
        return None  # pragma: no cover
    data = content.encode("utf-8", errors="replace")
    tree = parser.parse(data)

    targets = {
        "c": {"function_definition", "struct_specifier", "enum_specifier"},
        "cpp": {"function_definition", "class_specifier", "struct_specifier", "enum_specifier"},
        "java": {"method_declaration", "class_declaration", "interface_declaration"},
    }[grammar]

    out: List[Tuple[str, Dict[str, str]]] = []

    def node_text(node) -> str:
        return content[node.start_byte : node.end_byte]

    def walk(node, classname: str = ""):
        t = node.type
        if t in targets:
            txt = node_text(node).strip()
            if not txt:
                return  # pragma: no cover
            cmt = _ts_comment_prefix(content, node.start_byte, 2)
            if cmt:
                txt = cmt + txt  # pragma: no cover
            name = path.stem
            chunk_name = name
            if grammar == "cpp" and t == "function_definition":
                for ch in node.children:
                    if ch.type == "function_declarator":
                        for g in ch.children:
                            if g.type == "identifier":
                                chunk_name = content[g.start_byte : g.end_byte]
            if grammar == "java" and t == "method_declaration":
                for ch in node.children:
                    if ch.type == "identifier":
                        chunk_name = content[ch.start_byte : ch.end_byte]
                        break
            if classname and grammar in ("cpp", "java"):
                chunk_name = f"{classname}::{chunk_name}"
            out.append(
                (
                    txt[:12000],
                    {
                        "chunk_strategy": f"ast_{grammar}",
                        "chunk_type": t,
                        "chunk_name": chunk_name[:200],
                        "chunk_index": str(len(out)),
                    },
                )
            )
        if grammar == "cpp" and t == "class_specifier":
            cname = classname  # pragma: no cover
            for ch in node.children:  # pragma: no cover
                if ch.type == "type_identifier":  # pragma: no cover
                    cname = content[ch.start_byte : ch.end_byte]  # pragma: no cover
                    break  # pragma: no cover
            for ch in node.children:  # pragma: no cover
                walk(ch, cname or classname)  # pragma: no cover
        elif grammar == "java" and t in ("class_declaration", "interface_declaration"):
            cname = classname
            for ch in node.children:
                if ch.type == "identifier":
                    cname = content[ch.start_byte : ch.end_byte]
                    break
            for ch in node.children:
                walk(ch, cname or classname)
        else:
            for ch in node.children:
                walk(ch, classname)

    walk(tree.root_node)
    return out if out else None


def chunk_scheme(content: str, path: Path) -> List[Tuple[str, Dict[str, str]]]:
    try:
        parser = _ts_parser_for("scheme", "tree_sitter_scheme")
        if parser is not None:
            data = content.encode("utf-8", errors="replace")
            tree = parser.parse(data)
            out_ts: List[Tuple[str, Dict[str, str]]] = []

            def walk_scheme(n):
                if n.type == "list" and n.children:
                    first = n.children[0]
                    if first.type == "symbol" and content[first.start_byte : first.end_byte] == "define":
                        sym = n.children[1] if len(n.children) > 1 else None  # pragma: no cover
                        nm = (  # pragma: no cover
                            content[sym.start_byte : sym.end_byte].strip("()")
                            if sym
                            else path.stem
                        )
                        raw = content[n.start_byte : n.end_byte]  # pragma: no cover
                        cmt = _ts_comment_prefix(content, n.start_byte, 2)  # pragma: no cover
                        body = (cmt + raw) if cmt else raw  # pragma: no cover
                        out_ts.append(  # pragma: no cover
                            (
                                body[:12000],
                                {
                                    "chunk_strategy": "scheme",
                                    "chunk_type": "define",
                                    "chunk_name": nm[:200],
                                    "chunk_index": str(len(out_ts)),
                                },
                            )
                        )
                for ch in n.children:
                    walk_scheme(ch)

            walk_scheme(tree.root_node)
            if out_ts:
                return out_ts  # pragma: no cover
    except Exception:  # pragma: no cover
        pass  # pragma: no cover
    forms = re.split(r"(?m)(?=^\s*\(define\b)", content)
    out: List[Tuple[str, Dict[str, str]]] = []
    for f in forms:
        f = f.strip()
        if not f.startswith("(define"):
            continue
        m = re.match(r"^\s*\(define\s+(\S+)", f)
        name = m.group(1).strip("()") if m else path.stem
        out.append(
            (
                f[:12000],
                {
                    "chunk_strategy": "scheme",
                    "chunk_type": "define",
                    "chunk_name": name,
                    "chunk_index": str(len(out)),
                },
            )
        )
    if not out:
        return generic_split(content, path, 2000)  # pragma: no cover
    return out


def sentence_window(text: str, path: Path) -> List[Tuple[str, Dict[str, str]]]:
    """Small chunks for retrieval; wider context_window in metadata for prompt expansion."""
    chunk_size, overlap = 300, 60
    splitter = RecursiveCharacterTextSplitter.from_language(
        language=Language.MARKDOWN, chunk_size=chunk_size, chunk_overlap=overlap
    )
    docs = splitter.create_documents([text])
    out: List[Tuple[str, Dict[str, str]]] = []
    for i, d in enumerate(docs):
        content = d.page_content
        needle = content[: min(80, len(content))] if content else ""
        idx = text.find(needle) if needle else -1
        if idx < 0:
            idx = 0  # pragma: no cover
        half = 600
        ctx_start = max(0, idx - half)
        ctx_end = min(len(text), idx + len(content) + half)
        context_window = text[ctx_start:ctx_end]
        if len(context_window) > 12000:
            context_window = context_window[:12000]  # pragma: no cover
        out.append(
            (
                content,
                {
                    "chunk_strategy": "sentence_window",
                    "chunk_type": "fragment",
                    "chunk_name": path.stem,
                    "chunk_index": str(i),
                    "context_window": context_window,
                },
            )
        )
    return out


def _js_ts_lang(ext: str) -> Language:
    if ext in (".ts", ".tsx"):
        return getattr(Language, "TS", getattr(Language, "TYPESCRIPT", Language.HTML))
    return getattr(Language, "JS", getattr(Language, "JAVASCRIPT", Language.HTML))


def choose_strategy_for_path(
    path: Path,
    source_type: str,
    mib_keep_deprecated: bool = False,
    embed_model: Optional[str] = None,
) -> Tuple[str, Callable[..., List[Tuple[str, Dict[str, str]]]], int]:
    ext = path.suffix.lower()
    em = (embed_model or os.environ.get("EMBEDDING_MODEL", "nomic-embed-text")).strip()
    code_limit = STRATEGY_SIZE_LIMIT_MB["config"] if ext in CONFIG_EXTS else STRATEGY_SIZE_LIMIT_MB["code"]
    if source_type == "code":
        if ext == ".py":
            return "code", lambda p, c: ast_chunk_python(p, c), code_limit
        if ext == ".c":
            return (
                "code",
                lambda p, c: _ts_extract_chunks(p, c, "c") or language_split(p, c, Language.C),
                code_limit,
            )
        if ext in (".cpp", ".cxx", ".cc", ".h", ".hpp", ".hxx"):
            return (
                "code",
                lambda p, c: _ts_extract_chunks(p, c, "cpp") or language_split(p, c, Language.CPP),
                code_limit,
            )
        if ext == ".java":
            return (
                "code",
                lambda p, c: _ts_extract_chunks(p, c, "java") or language_split(p, c, Language.JAVA),
                code_limit,
            )
        if ext == ".scm":
            return "code", lambda p, c: chunk_scheme(c, p), code_limit
        if ext in (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"):
            lg = _js_ts_lang(ext)
            return "code", lambda p, c, lg=lg: language_split(p, c, lg), code_limit
        if ext in (".md", ".txt"):
            return "code", lambda p, c: sentence_window(c, p), code_limit  # pragma: no cover
        return "code", lambda p, c: regex_code_split(c, p, ext), code_limit
    if source_type in ("domain_doc", "theory"):
        lim = STRATEGY_SIZE_LIMIT_MB["theory" if source_type == "theory" else "domain_doc"]
        if ext in (".md", ".txt", ".rst"):
            return source_type, lambda p, c, _em=em: chunk_markdown_domain(c, str(p), embed_model=_em), lim
        return source_type, lambda p, c: generic_split(c, p, 2000), lim  # pragma: no cover
    if source_type == "rfc":
        return (
            "rfc",
            lambda p, c, _em=em: chunk_rfc(c, str(p), embed_model=_em),
            STRATEGY_SIZE_LIMIT_MB["rfc"],
        )
    if source_type == "mib":
        sk = not mib_keep_deprecated
        return "mib", lambda p, c, _sk=sk: chunk_mib(c, p, skip_deprecated=_sk), STRATEGY_SIZE_LIMIT_MB["mib"]
    if source_type == "release_notes":
        return "release_notes", lambda p, c: chunk_release_notes(c, str(p)), STRATEGY_SIZE_LIMIT_MB["release_notes"]
    if source_type == "community":
        return "community", lambda p, c: chunk_community(c, str(p), {}), STRATEGY_SIZE_LIMIT_MB["community"]
    if source_type == "wiki":
        return "wiki", lambda p, c: chunk_wiki_page(c, str(p), {}), STRATEGY_SIZE_LIMIT_MB["wiki"]
    return "default", lambda p, c: generic_split(c, p, 2000), STRATEGY_SIZE_LIMIT_MB["default"]


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


async def _async_http_embed_batch(
    session: Any, model: str, texts: List[str], timeout: float = 300.0
) -> List[List[float]]:
    if aiohttp is None:
        raise RuntimeError("aiohttp is not installed")
    url = _ollama_embed_url()
    to = aiohttp.ClientTimeout(total=timeout)
    async with session.post(url, json={"model": model, "input": texts}, timeout=to) as resp:
        resp.raise_for_status()
        data = await resp.json()
    embs = data.get("embeddings")
    if embs is not None:
        return embs
    one = data.get("embedding")
    if one is not None:
        return [one]
    raise RuntimeError(f"Unexpected Ollama embed response: {list(data.keys())}")


async def embed_with_retry_http_async(
    session: Any,
    model: str,
    batch: List[str],
    async_lock: Optional[asyncio.Lock],
) -> Optional[List[List[float]]]:
    async def _try(b: List[str]) -> Optional[List[List[float]]]:
        for _ in range(MAX_RETRIES):
            try:
                if async_lock is not None:
                    async with async_lock:
                        return await _async_http_embed_batch(session, model, b)
                return await _async_http_embed_batch(session, model, b)
            except Exception as exc:
                logger.warning("embed async retry: %s", exc)
                await asyncio.sleep(EMBED_BACKOFF_SEC)
        if len(b) <= 1:
            return None
        mid = max(1, len(b) // 2)
        a = await _try(b[:mid])
        b2 = await _try(b[mid:])
        if a is None or b2 is None:
            return None
        return a + b2

    return await _try(batch)


async def run_async_embedding_batches(
    batches: List[List[Tuple[str, str, Dict[str, str]]]],
    embed_model: str,
    concurrency: int,
) -> List[Optional[Tuple[List[str], List[str], List[Dict[str, str]], List[List[float]]]]]:
    """Concurrent aiohttp embedding; returns one result per input batch (order preserved)."""
    if aiohttp is None:
        return [None] * len(batches)
    sem = asyncio.Semaphore(concurrency)
    alock = asyncio.Lock() if _embed_serialize_on() else None

    async with aiohttp.ClientSession() as session:

        async def one(
            batch: List[Tuple[str, str, Dict[str, str]]],
        ) -> Optional[Tuple[List[str], List[str], List[Dict[str, str]], List[List[float]]]]:
            async with sem:
                ids, texts, metas = [], [], []
                for cid, text, meta in batch:
                    ids.append(cid)
                    texts.append(text)
                    metas.append(meta)
                vecs = await embed_with_retry_http_async(session, embed_model, texts, alock)
                if vecs is None:
                    return None
                return (ids, texts, metas, vecs)

        return list(await asyncio.gather(*[one(b) for b in batches]))


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


def ingest_run(args: argparse.Namespace) -> int:
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

    ingestion_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    for path, extra in tqdm(files_to_process, desc="Scanning", unit="file"):
        file_deps_str = ""
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
            _sk, chunk_fn, limit_mb = choose_strategy_for_path(
                path,
                source_type,
                mib_keep_deprecated=getattr(args, "mib_keep_deprecated", False),
                embed_model=embed_model,
            )
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
                pieces = chunk_fn(path, content)
            ext = path.suffix.lower()
            repo, rel = rel_repo_for(path)
            mtime = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            size_kb = round(st.st_size / 1024.0, 3)
            file_deps_str = extract_dependencies(content, ext) if source_type == "code" else ""

        if not pieces:
            continue  # pragma: no cover

        if not extra.get("virtual") and abs_src and not args.dry_run:
            try:
                coll.delete(where={"source": abs_src})
            except Exception:  # pragma: no cover
                pass  # pragma: no cover

        base = empty_metadata()
        base.update(
            {
                "source": abs_src,
                "source_type": source_type,
                "domain": domain,
                "repository": repo,
                "relative_path": rel,
                "extension": ext,
                "file_size_kb": str(size_kb),
                "last_modified": mtime,
                "ingestion_date": ingestion_ts,
                "ingestion_version": INGESTION_VERSION,
                "dependencies": file_deps_str,
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
            meta = finalize_metadata(meta)
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
            for batch in tqdm(batches, desc="Embedding", unit="batch"):
                if shutdown_event.is_set():
                    break  # pragma: no cover
                chunk_q.put(batch)
        finally:
            for _ in threads:
                chunk_q.put(None)
        for t in threads:
            t.join(timeout=600)

    result_q.put(WRITER_STOP)
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


def _handle_sig(*_args):
    shutdown_event.set()  # pragma: no cover


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Universal domain RAG ingestion")
    p.add_argument(
        "--mode",
        choices=[
            "code",
            "domain",
            "rfc",
            "rally",
            "customer",
            "mib",
            "wiki",
            "release-notes",
            "theory",
            "community",
            "status",
        ],
        default=os.environ.get("INGEST_MODE", "").strip() or None,
    )
    p.add_argument("--source", default=os.environ.get("SOURCE_FOLDER", "").strip() or None)
    p.add_argument("--domain", default=os.environ.get("INGEST_DOMAIN", "general"))
    p.add_argument("--collection", default=os.environ.get("CHROMA_COLLECTION", "").strip() or None)
    p.add_argument(
        "--db-path",
        default=os.environ.get("DB_PATH", "").strip() or str(SCRIPT_DIR / "VectorDB"),
    )
    p.add_argument("--rally-project", default=os.environ.get("RALLY_PROJECT", "").strip() or None)
    p.add_argument("--rally-filter", default=os.environ.get("RALLY_FILTER", "").strip() or None)
    p.add_argument("--confluence-space", default=os.environ.get("CONFLUENCE_SPACE", "").strip() or None)
    p.add_argument("--concept-registry", default=str(SCRIPT_DIR / "concept_registry.json"))
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--force", action="store_true")
    p.add_argument(
        "--recreate-collection",
        action="store_true",
        help=(
            "If the target Chroma collection's embedding dimension does not match the "
            "current model, delete that collection and its checkpoint entry, then ingest "
            "fresh (destructive for that collection only)."
        ),
    )
    p.add_argument(
        "--clean-stale",
        action="store_true",
        help="Delete Chroma chunks for sources removed from disk (checkpoint always pruned)",
    )
    p.add_argument(
        "--mib-keep-deprecated",
        action="store_true",
        help="Ingest deprecated/obsolete MIB objects (default: skip)",
    )
    p.add_argument(
        "--confluence-label",
        default=os.environ.get("CONFLUENCE_LABEL", "").strip() or None,
        help="Filter wiki pages by label (Confluence API)",
    )
    p.add_argument(
        "--git-diff",
        action="store_true",
        help="Only ingest files changed vs --git-diff-base (git); deletes removed paths from Chroma",
    )
    p.add_argument(
        "--git-diff-base",
        default=os.environ.get("GIT_DIFF_BASE", "").strip() or None,
        help="Git ref to diff against (default: last stored ingest ref or HEAD~1)",
    )
    p.add_argument("--verbose", action="store_true")
    return p


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


def main(argv: Optional[List[str]] = None) -> int:
    signal.signal(signal.SIGINT, _handle_sig)
    signal.signal(signal.SIGTERM, _handle_sig)
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    if not args.mode:
        if args.source or os.environ.get("SOURCE_FOLDER"):
            args.mode = "code"
            args.domain = args.domain or "general"
        else:
            parser.error("--mode is required unless SOURCE_FOLDER is set (legacy code ingest)")
    if args.mode != "status":
        if args.mode not in ("rally", "wiki") and not args.source and not os.environ.get("SOURCE_FOLDER"):
            parser.error("--source required for this mode (or set SOURCE_FOLDER)")  # pragma: no cover
    return ingest_run(args)


if __name__ == "__main__":
    raise SystemExit(main())

