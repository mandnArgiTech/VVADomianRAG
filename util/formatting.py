"""util/formatting.py — Result and chunk formatting for VVADomainRAG."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, Dict, List, Optional

from util.constants import LANG_TAG, RESULT_CHUNK_MAX_CHARS, RESULT_CONTEXT_WINDOW_MAX_CHARS


def infer_source_type(meta: Dict[str, Any]) -> str:
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


def fence_for(content: str) -> str:
    return "~~~" if "```" in content else "```"


def truncate_chunk(text: str, max_chars: Optional[int] = None) -> str:
    """Truncate with newline / `}`-aware cut; close dangling ``` fences if needed."""
    mx = max_chars if max_chars is not None and max_chars > 0 else RESULT_CHUNK_MAX_CHARS
    if len(text) <= mx:
        return text
    suffix = "\n\n... (truncated) ..."
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
    """Prefer ``context_window`` over page_content; larger cap + syntax-aware ``truncate_chunk``."""
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
    content = truncate_chunk(raw_body, trunc_limit)
    ext = (meta.get("extension") or "").lower()

    if source_type == "callee":
        if repo:
            header.append(f"**Repo:** {repo}")
        header.append(f"**File:** {repo + '/' + src if repo else src}")
        if cname:
            header.append(f"**Component:** {cname} ({ctype})")
        si = int(meta.get("structural_importance", 0) or 0)
        if si > 0:
            header.append(f"**importance:** {si}")
        lang = LANG_TAG.get(ext, "")
        fence = fence_for(content)
        return "### Callee (auto-expanded)\n" + "\n".join(header) + f"\n\n{fence}{lang}\n{content}\n{fence}"

    if source_type == "code":
        if repo:
            header.append(f"**Repo:** {repo}")
        header.append(f"**File:** {repo + '/' + src if repo else src}")
        if cname:
            header.append(f"**Component:** {cname} ({ctype})")
        si = int(meta.get("structural_importance", 0) or 0)
        if si > 0:
            header.append(f"**importance:** {si}")
        dep = (meta.get("dependencies") or "").strip()
        if dep:
            dshow = dep if len(dep) <= 500 else dep[:500] + "…"
            header.append(f"**dependencies:** {dshow}")
        calls_str = (meta.get("calls") or "").strip()
        if calls_str:
            s = calls_str.strip("|")
            raw_calls = (
                [x.strip() for x in s.split("|") if x.strip()]
                if "|" in calls_str
                else [x.strip() for x in calls_str.split(",") if x.strip()]
            )
            callees_list = [c for c in raw_calls if c != "__truncated__"][:15]
            if callees_list:
                header.append(f"**Callees (Outgoing):** {', '.join(callees_list)}")
        if meta.get("retrieval_hop") == "caller":
            header.append("**[CALLER NODE]** This chunk calls the primary retrieved function.")
        lang = LANG_TAG.get(ext, "")
        fence = fence_for(content)
        return "### Code\n" + "\n".join(header) + f"\n\n{fence}{lang}\n{content}\n{fence}"

    if source_type in ("domain_doc", "theory", "wiki"):
        sec = meta.get("section", meta.get("doc_title", "Domain Knowledge"))
        src_files = (meta.get("source_c_files") or "").strip()
        rel_block = ""
        if src_files:
            rel_block = "\n\n## Related source files\n\n" + ", ".join(
                x.strip() for x in src_files.split(",") if x.strip()
            )
        return f"### {sec}\n*Source: {meta.get('source', '')}*{rel_block}\n\n{content}"

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


def format_markdown(hits: List[Any], query: str) -> str:
    if not hits:
        return "No matching chunks found."
    fake_docs = []
    for h in hits:
        doc = type("D", (), {"page_content": h.content, "metadata": h.metadata})()
        fake_docs.append(format_result(doc, h.score, h.source_type))
    return "\n\n---\n\n".join(fake_docs)


def format_concept_markdown(hits: List[Any], concept: str) -> str:
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


def format_json_output(query: str, hits: List[Any], mode: str, answer: str = "") -> str:
    payload: Dict[str, Any] = {
        "query": query,
        "mode": mode,
        "results": [asdict(h) for h in hits],
    }
    if answer:
        payload["answer"] = answer
    return json.dumps(payload, indent=2)


def format_plain(hits: List[Any]) -> str:
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
