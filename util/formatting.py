"""
util/formatting.py — Result formatting for RAG hits.

Previously duplicated across query.py and mcp_server.py.  The two versions had
diverged: mcp_server had a ``callee`` source_type branch and surfaced
``structural_importance`` / ``source_c_files``; query.py did not.  This module
merges both into one authoritative implementation.

Public API
----------
infer_source_type(meta)                             str
fence_for(content)                                  str
truncate_chunk(text, max_chars, truncate_label)     str
format_result(doc, score, source_type,
              result_chunk_max_chars,
              result_context_window_max_chars,
              metadata_token_fn)                    str
format_markdown(hits, query)                        str
format_concept_markdown(hits, concept)              str
format_plain(hits)                                  str
format_json_output(hits, query, k, search_type,
                   domain, db_path)                 str
"""

from __future__ import annotations

import json
import os
from typing import Any, Callable, Dict, List, Optional

from util.constants import LANG_TAG

__all__ = [
    "infer_source_type",
    "fence_for",
    "truncate_chunk",
    "format_result",
    "format_markdown",
    "format_concept_markdown",
    "format_plain",
    "format_json_output",
]

# ---------------------------------------------------------------------------
# Env-driven size caps (callers may override per-call via arguments)
# ---------------------------------------------------------------------------

_RESULT_CHUNK_MAX_CHARS = max(512, int(os.environ.get("MCP_RESULT_CHUNK_MAX_CHARS", "4096")))
_RESULT_CONTEXT_WINDOW_MAX_CHARS = max(
    _RESULT_CHUNK_MAX_CHARS,
    int(os.environ.get("MCP_RESULT_CONTEXT_WINDOW_MAX_CHARS", "16000")),
)


# ---------------------------------------------------------------------------
# Source-type inference
# ---------------------------------------------------------------------------

def infer_source_type(meta: Dict[str, Any]) -> str:
    """Infer source_type from metadata fields when the field itself is absent."""
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


# ---------------------------------------------------------------------------
# Fence + truncation
# ---------------------------------------------------------------------------

def fence_for(content: str) -> str:
    """Return ~~~ when content already contains ``` fences, else ```."""
    return "~~~" if "```" in content else "```"


def truncate_chunk(
    text: str,
    max_chars: Optional[int] = None,
    *,
    truncate_label: str = "... (truncated for response size) ...",
) -> str:
    """Truncate *text* at a natural boundary; close any dangling ``` fence.

    Parameters
    ----------
    text:
        Raw chunk text.
    max_chars:
        Hard cap.  Defaults to ``MCP_RESULT_CHUNK_MAX_CHARS`` env var (4096).
    truncate_label:
        Suffix appended after the cut point.
    """
    mx = max_chars if max_chars is not None and max_chars > 0 else _RESULT_CHUNK_MAX_CHARS
    if len(text) <= mx:
        return text
    suffix = f"\n\n{truncate_label}"
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


# ---------------------------------------------------------------------------
# Single-hit formatter
# ---------------------------------------------------------------------------

def format_result(
    doc: Any,
    score: Optional[float],
    source_type: str,
    *,
    result_chunk_max_chars: Optional[int] = None,
    result_context_window_max_chars: Optional[int] = None,
    metadata_token_fn: Optional[Callable[[str], List[str]]] = None,
    structural_importance_fn: Optional[Callable[[Optional[Dict[str, Any]]], int]] = None,
) -> str:
    """Render one RAG hit as a Markdown string.

    Parameters
    ----------
    doc:
        LangChain ``Document`` (must have ``.metadata`` and ``.page_content``).
    score:
        Distance score (lower = more similar) or None.
    source_type:
        Resolved source type string (see ``infer_source_type``).
    result_chunk_max_chars / result_context_window_max_chars:
        Per-call size caps; fall back to env-var defaults when omitted.
    metadata_token_fn:
        Callable(raw_str) → List[str] used to split pipe/comma metadata fields
        like ``calls``.  Defaults to a simple comma-split.
    structural_importance_fn:
        Callable(meta) → int returning the structural_importance integer.
        Pass None to skip importance display.
    """
    chunk_cap = result_chunk_max_chars or _RESULT_CHUNK_MAX_CHARS
    ctx_cap = result_context_window_max_chars or _RESULT_CONTEXT_WINDOW_MAX_CHARS

    if metadata_token_fn is None:
        def metadata_token_fn(raw: str) -> List[str]:  # type: ignore[misc]
            s = (raw or "").strip()
            if not s:
                return []
            if s.startswith("|"):
                return [x.strip() for x in s.strip("|").split("|") if x.strip()]
            return [x.strip() for x in s.split(",") if x.strip()]

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
        trunc_limit = ctx_cap
    else:
        raw_body = (doc.page_content or "").strip()
        trunc_limit = chunk_cap
    content = truncate_chunk(raw_body, trunc_limit)
    ext = (meta.get("extension") or "").lower()

    # -- callee (auto-expanded by mcp_server callee-expand pass) -----------
    if source_type == "callee":
        if repo:
            header.append(f"**Repo:** {repo}")
        header.append(f"**File:** {repo + '/' + src if repo else src}")
        if cname:
            header.append(f"**Component:** {cname} ({ctype})")
        if structural_importance_fn is not None:
            si = structural_importance_fn(meta)
            if si > 0:
                header.append(f"**importance:** {si}")
        lang = LANG_TAG.get(ext, "")
        fence = fence_for(content)
        return "### Callee (auto-expanded)\n" + "\n".join(header) + f"\n\n{fence}{lang}\n{content}\n{fence}"

    # -- code ---------------------------------------------------------------
    if source_type == "code":
        if repo:
            header.append(f"**Repo:** {repo}")
        header.append(f"**File:** {repo + '/' + src if repo else src}")
        if cname:
            header.append(f"**Component:** {cname} ({ctype})")
        if structural_importance_fn is not None:
            si = structural_importance_fn(meta)
            if si > 0:
                header.append(f"**importance:** {si}")
        dep = (meta.get("dependencies") or "").strip()
        if dep:
            dshow = dep if len(dep) <= 500 else dep[:500] + "…"
            header.append(f"**dependencies:** {dshow}")
        calls_str = (meta.get("calls") or "").strip()
        if calls_str:
            callees_list = [c for c in metadata_token_fn(calls_str) if c != "__truncated__"][:15]
            if callees_list:
                header.append(f"**Callees (Outgoing):** {', '.join(callees_list)}")
        if meta.get("retrieval_hop") == "caller":
            header.append("**[CALLER NODE]** This chunk calls the primary retrieved function.")
        lang = LANG_TAG.get(ext, "")
        fence = fence_for(content)
        return "### Code\n" + "\n".join(header) + f"\n\n{fence}{lang}\n{content}\n{fence}"

    # -- domain doc / theory / wiki ----------------------------------------
    if source_type in ("domain_doc", "theory", "wiki"):
        sec = meta.get("section", meta.get("doc_title", "Domain Knowledge"))
        src_files = (meta.get("source_c_files") or "").strip()
        rel_block = ""
        if src_files:
            rel_block = "\n\n## Related source files\n\n" + ", ".join(
                x.strip() for x in src_files.split(",") if x.strip()
            )
        return f"### {sec}\n*Source: {meta.get('source', '')}*{rel_block}\n\n{content}"

    # -- RFC ----------------------------------------------------------------
    if source_type == "rfc":
        rfc = meta.get("rfc_number", "")
        sec_num = meta.get("section_number", "")
        sec_title = meta.get("section_title", "")
        head = f"RFC {rfc} §{sec_num}"
        if sec_title:
            head += f": {sec_title}"
        return f"### {head}\n\n{content}"

    # -- Rally / customer tickets -------------------------------------------
    if source_type in ("rally", "customer"):
        tid = meta.get("rally_id", "") or meta.get("ticket_id", "")
        title = meta.get("chunk_name", "") or meta.get("Name", "")
        res = meta.get("has_resolution", "") == "true"
        line = f"[{tid}] {title}" if title else f"[{tid}]"
        if res:
            line += " — Resolution: (see body)"
        return f"### {line}\n\n{content}"

    # -- MIB ----------------------------------------------------------------
    if source_type == "mib":
        oid = meta.get("object_name", "")
        path = meta.get("oid_path", "")
        return f"### OID: {oid} ({path}) — Description\n\n{content}"

    # -- Community posts ----------------------------------------------------
    if source_type == "community":
        plat = meta.get("source_platform", "unknown")
        return f"### Source: [{plat}] — {meta.get('source_url', '')}\n\n{content}"

    # -- generic fallback ---------------------------------------------------
    return "### Result\n" + "\n".join(header) + f"\n\n{content}"


# ---------------------------------------------------------------------------
# Multi-hit formatters
# ---------------------------------------------------------------------------

def format_markdown(hits: list, query: str) -> str:
    """Render a list of SearchHit objects as Markdown."""
    if not hits:
        return "_No results._"
    parts: List[str] = []
    for h in hits:
        parts.append(
            format_result(
                _hit_to_doc(h),
                h.score,
                h.source_type,
            )
        )
    return "\n\n---\n\n".join(parts)


def format_concept_markdown(hits: list, concept: str) -> str:
    """Render concept-search hits as Markdown."""
    if not hits:
        return f"_No chunks found for concept `{concept}`._"
    parts: List[str] = []
    for h in hits:
        parts.append(
            format_result(
                _hit_to_doc(h),
                h.score,
                h.source_type,
            )
        )
    return f"## Concept: `{concept}`\n\n" + "\n\n---\n\n".join(parts)


def format_plain(hits: list) -> str:
    """Plain-text rendering for terminal output."""
    lines: List[str] = []
    for i, h in enumerate(hits, 1):
        meta = h.metadata or {}
        src = meta.get("source", meta.get("relative_path", ""))
        score_str = f"  score={h.score:.4f}" if h.score is not None else ""
        lines.append(f"[{i}] {h.source_type}{score_str}  {src}")
        lines.append(h.content[:300].replace("\n", " "))
        lines.append("")
    return "\n".join(lines)


def format_json_output(
    hits: list,
    query: str,
    k: int,
    search_type: str,
    domain: str,
    db_path: str,
) -> str:
    """Render hits as a JSON string (for --output json CLI mode)."""
    records = []
    for h in hits:
        records.append(
            {
                "content": h.content,
                "score": h.score,
                "source_type": h.source_type,
                "metadata": h.metadata or {},
                "collection": getattr(h, "collection", None),
            }
        )
    return json.dumps(
        {
            "query": query,
            "k": k,
            "search_type": search_type,
            "domain": domain,
            "db_path": db_path,
            "results": records,
        },
        indent=2,
        default=str,
    )


# ---------------------------------------------------------------------------
# Internal helper: SearchHit → thin Document-like wrapper
# ---------------------------------------------------------------------------

class _HitDoc:
    """Minimal Document proxy so format_result works with SearchHit objects."""

    __slots__ = ("page_content", "metadata")

    def __init__(self, content: str, metadata: Dict[str, Any]) -> None:
        self.page_content = content
        self.metadata = metadata


def _hit_to_doc(hit: Any) -> _HitDoc:
    return _HitDoc(
        content=getattr(hit, "content", "") or "",
        metadata=dict(getattr(hit, "metadata", None) or {}),
    )
