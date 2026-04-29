"""Community Q&A and Confluence wiki chunkers."""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

from ingest_kit.chunking.html_utils import strip_html
from ingest_kit.chunking.markdown import chunk_markdown_domain


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
