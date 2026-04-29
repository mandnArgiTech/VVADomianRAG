"""Paragraph packing and min-size merging for markdown/RFC chunks."""

from __future__ import annotations

import os
import re
from typing import Dict, List, Optional, Tuple

from ingest_kit.chunking.shared import (
    _is_diagram_placeholder,
    _protect_math_blocks,
    _restore_math_blocks,
)
from ingest_kit.concepts import format_concepts_field, iter_concept_ids


def _merge_min_chunk_sidecar_metadata(buf: Dict[str, str], incoming: Dict[str, str]) -> None:
    """When min-size merge concatenates bodies, union pipe-token fields (e.g. ``calls``, ``concepts``).

    File-scoped keys (``source_c_files``, ``dependencies``, ``doc_title``, …) stay from the first
    chunk only (Story F).
    """
    for key in ("calls", "concepts"):
        ids = sorted(
            set(iter_concept_ids(str(buf.get(key) or "")))
            | set(iter_concept_ids(str(incoming.get(key) or "")))
        )
        ids = [i for i in ids if i != "__truncated__"]
        if ids:
            buf[key] = format_concepts_field(ids)


def _split_paragraphs(
    text: str, target_min: int = 2000, target_max: int = 5000, protect_math: bool = False
) -> List[str]:
    """Token-aware paragraph packer with diagram-context bonding."""
    math_vault: List[str] = []
    if protect_math:
        text, math_vault = _protect_math_blocks(text)
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
    if math_vault:
        out = [_restore_math_blocks(seg, math_vault) for seg in out]
    return out


def _top_section(meta: Dict[str, str]) -> str:
    """Boundary key for min-size merging: same top-level ``##`` / RFC section only."""
    sec = (meta.get("section") or "").strip()
    if sec:
        parts = sec.split(" > ")
        if len(parts) >= 2:
            return " > ".join(parts[:2])
        return sec
    sec_num = (meta.get("section_number") or "").strip()
    if sec_num:
        return sec_num.split(".")[0]
    return (meta.get("section_title") or "").strip()


def _merge_small_chunks(
    chunks: List[Tuple[str, Dict[str, str]]],
    min_size: int = 500,
    max_size: int = 5000,
) -> List[Tuple[str, Dict[str, str]]]:
    """Merge adjacent undersized chunks within the same top-level section (Story F)."""
    if not chunks or min_size <= 0:
        return list(chunks)

    out: List[Tuple[str, Dict[str, str]]] = []
    buf_text = ""
    buf_meta: Optional[Dict[str, str]] = None
    buf_section = ""

    for text, meta in chunks:
        cur_section = _top_section(meta)

        if not buf_text:
            buf_text = text
            buf_meta = dict(meta)
            buf_section = cur_section
            continue

        same_section = cur_section == buf_section
        buf_small = len(buf_text) < min_size
        next_small = len(text) < min_size
        merged_len = len(buf_text) + len(text) + 2

        if same_section and buf_small and next_small and merged_len <= max_size:
            buf_text = buf_text + "\n\n" + text
            if buf_meta is not None:
                _merge_min_chunk_sidecar_metadata(buf_meta, meta)
        else:
            if buf_meta is not None:
                out.append((buf_text, buf_meta))
            buf_text = text
            buf_meta = dict(meta)
            buf_section = cur_section

    if buf_text and buf_meta is not None:
        out.append((buf_text, buf_meta))

    for i, (_, m) in enumerate(out):
        m["chunk_index"] = str(i)

    return out


def _apply_chunk_min_merge(
    chunks: List[Tuple[str, Dict[str, str]]], max_size: int
) -> List[Tuple[str, Dict[str, str]]]:
    raw = os.environ.get("CHUNK_MIN_SIZE", "500")
    try:
        min_sz = int(raw)
    except ValueError:
        min_sz = 500
    if min_sz > 0 and len(chunks) > 1:
        return _merge_small_chunks(chunks, min_size=min_sz, max_size=max_size)
    return chunks
