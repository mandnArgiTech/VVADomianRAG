"""util/chunk_metadata.py — Metadata field parsing for RAG chunks."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def metadata_pipe_or_comma_tokens(raw: str) -> List[str]:
    """Split pipe- or comma-delimited metadata fields (calls, concepts)."""
    s = (raw or "").strip()
    if not s:
        return []
    if s.startswith("|"):
        return [x.strip() for x in s.strip("|").split("|") if x.strip()]
    return [x.strip() for x in s.split(",") if x.strip()]


def parse_dependency_tokens(deps: str) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for part in (deps or "").split(","):
        t = part.strip()
        if not t or t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out


def depend_stems_from_results(
    results: List[Tuple[Any, Optional[float], str]],
) -> List[str]:
    stems: set = set()
    for doc, _, _ in results:
        meta = getattr(doc, "metadata", None) or {}
        rel = str(meta.get("relative_path") or "").strip()
        if rel:
            stem = Path(rel).stem
            if stem:
                stems.add(stem)
            stems.add(Path(rel.replace("\\", "/")).name)
        cn = str(meta.get("chunk_name") or "").strip()
        if cn:
            stems.add(cn)
    return sorted(stems)


def dependencies_where_comma_token(stem: str) -> Dict[str, Any]:
    """Chroma $or filter matching stem as a whole comma-delimited entry."""
    s = (stem or "").strip()
    if not s:
        return {"dependencies": {"$eq": "__empty_dependency_stem__"}}
    return {
        "$or": [
            {"dependencies": {"$eq": s}},
            {"dependencies": {"$contains": f"{s}, "}},
            {"dependencies": {"$contains": f", {s}, "}},
            {"dependencies": {"$contains": f", {s}"}},
        ]
    }


def iter_concept_ids(concepts_field: str) -> List[str]:
    """Split the concepts metadata field — re-export for single import location."""
    return metadata_pipe_or_comma_tokens(concepts_field)
