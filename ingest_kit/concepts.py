"""Concept registry formatting helpers (pipe-delimited metadata)."""

from __future__ import annotations

from typing import Iterable, List


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
