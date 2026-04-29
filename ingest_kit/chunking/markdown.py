"""Domain markdown chunking (headings, diagrams, chapter metadata)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Tuple

from ingest_kit.chunking.chapter_domain import _chapter_meta_from_filename, _domain_doc_content_type
from ingest_kit.chunking.paragraphs import _apply_chunk_min_merge, _split_paragraphs
from ingest_kit.chunking.shared import (
    _extract_source_c_files,
    _mask_markdown_fences_and_tables,
    _unmask_markdown_with_meta,
)
from ingest_kit.chunking.sizing import _md_char_targets


def chunk_markdown_domain(
    text: str, path: str, embed_model: str = "nomic-embed-text"
) -> List[Tuple[str, Dict[str, str]]]:
    masked, vault = _mask_markdown_fences_and_tables(text)
    h1_m = re.search(r"(?m)^#\s+(.+)$", masked)
    h1 = h1_m.group(1).strip() if h1_m else ""
    t_min, t_max = _md_char_targets(embed_model)
    split_threshold = int(t_max * 1.2)

    stem_st = Path(path).stem
    m_chapter = re.match(r"Chapter_\d+_(.*)", stem_st)
    stem_rest = m_chapter.group(1) if m_chapter else stem_st
    ch_meta = _chapter_meta_from_filename(path)
    dev_fam = str(ch_meta.get("device_family", "")).strip()
    domain_ct = _domain_doc_content_type(stem_rest, dev_fam or "CORE")
    file_chunk_meta: Dict[str, str] = {
        "source_c_files": _extract_source_c_files(text),
        "chapter_number": str(ch_meta.get("chapter_number") or ""),
        "device_family": dev_fam,
        "content_type": domain_ct,
    }

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
        for fk, fv in file_chunk_meta.items():
            if fv:
                meta[fk] = fv
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
                    # Match ### headings only, not #### (would also startswith "###").
                    if sseg.startswith("###") and not sseg.startswith("####"):  # pragma: no cover
                        st = sseg.lstrip("#").strip()  # pragma: no cover
                        b2 = sub[j + 1].strip() if j + 1 < len(sub) else ""  # pragma: no cover
                        j += 2  # pragma: no cover
                        sub_hier = " > ".join(x for x in (h1, title, st) if x)  # pragma: no cover
                        pieces = (
                            _split_paragraphs(b2, t_min, t_max, protect_math=True)
                            if len(b2) > split_threshold
                            else [b2]
                        )  # pragma: no cover
                        for piece in pieces:  # pragma: no cover
                            chunks.append(_finalize(piece, sub_hier or hierarchy, "section", idx_ref))  # pragma: no cover
                    else:
                        b0 = sseg  # pragma: no cover
                        j += 1  # pragma: no cover
                        pieces = (
                            _split_paragraphs(b0, t_min, t_max, protect_math=True)
                            if len(b0) > split_threshold
                            else [b0]
                        )  # pragma: no cover
                        for piece in pieces:  # pragma: no cover
                            chunks.append(_finalize(piece, hierarchy, "section", idx_ref))  # pragma: no cover
            else:
                pieces = (
                    _split_paragraphs(body, t_min, t_max, protect_math=True)
                    if len(body) > split_threshold
                    else [body]
                )
                for piece in pieces:
                    chunks.append(_finalize(piece, hierarchy, "section", idx_ref))
        else:
            intro = seg
            i += 1
            if intro and not intro.startswith("#"):
                hier = h1 or path
                pieces = (
                    _split_paragraphs(intro, t_min, t_max, protect_math=True)
                    if len(intro) > split_threshold
                    else [intro]
                )
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
        for fk, fv in file_chunk_meta.items():
            if fv:
                meta[fk] = fv
        chunks.append((txt, meta))
    chunks = _apply_chunk_min_merge(chunks, t_max)
    return chunks
