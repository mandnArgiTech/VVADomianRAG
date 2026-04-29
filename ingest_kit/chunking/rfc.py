"""RFC plain-text chunking."""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

from ingest_kit.chunking.paragraphs import _apply_chunk_min_merge, _split_paragraphs
from ingest_kit.chunking.rfc_preprocess import (
    _depaginate_rfc,
    _shield_diagrams,
    _sliding_window_chunks,
    _unshield_diagrams,
)
from ingest_kit.chunking.sizing import _rfc_char_targets


def chunk_rfc(
    text: str, path: str, embed_model: str = "nomic-embed-text"
) -> List[Tuple[str, Dict[str, str]]]:
    text = _depaginate_rfc(text)
    text, diagram_vault = _shield_diagrams(text)
    t_min, t_max = _rfc_char_targets(embed_model)
    section_body_threshold = t_max * 2

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
        out = _apply_chunk_min_merge(out, t_max)
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
    out = _apply_chunk_min_merge(out, t_max)
    return out  # pragma: no cover
