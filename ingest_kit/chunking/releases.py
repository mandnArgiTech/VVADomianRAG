"""Release notes / changelog chunking."""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

from ingest_kit.chunking.paragraphs import _split_paragraphs
from ingest_kit.chunking.shared import _extract_release_date_near_version


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
