"""Build LLM context strings from ranked ``SearchHit`` rows."""

from __future__ import annotations

from typing import List, Optional

from util.formatting import truncate_chunk as _truncate_chunk
from util.search_primitives import SearchHit

from query_kit.config import RAG_CONTEXT_MAX_CHARS


def build_context_blocks(hits: List[SearchHit], max_chars: Optional[int] = None) -> str:
    """Build the RAG context string for the LLM prompt."""
    budget = max_chars if max_chars and max_chars > 0 else RAG_CONTEXT_MAX_CHARS
    blocks: List[str] = []
    total = 0
    for i, h in enumerate(hits, 1):
        meta = h.metadata or {}
        src_raw = meta.get("relative_path") or meta.get("source", "?")
        src = src_raw if len(src_raw) <= 120 else "…/" + "/".join(str(src_raw).split("/")[-3:])
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
            blocks.append(
                f"\n[... {remaining} more chunk(s) omitted — context budget {budget:,} chars reached]"
            )
            break
        blocks.append(block)
        total += len(block)
    return "\n\n---\n\n".join(blocks)


_build_context_blocks = build_context_blocks
