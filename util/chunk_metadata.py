"""
util/chunk_metadata.py — Metadata field parsing for RAG chunks.

Previously duplicated across query.py and mcp_server.py (and partly in ingest.py).
Single source of truth for token splitting, dependency stem extraction, and the
Chroma ``$or`` filter builders.

Public API
----------
metadata_pipe_or_comma_tokens(raw)          List[str]
parse_dependency_tokens(deps)               List[str]
depend_stems_from_results(results)          List[str]
dependencies_where_comma_token(stem)        Dict[str, Any]
iter_concept_ids(concepts_field)            List[str]   (re-exported from ingest)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

__all__ = [
    "metadata_pipe_or_comma_tokens",
    "parse_dependency_tokens",
    "depend_stems_from_results",
    "dependencies_where_comma_token",
    "iter_concept_ids",
]


# ---------------------------------------------------------------------------
# Token splitting
# ---------------------------------------------------------------------------

def metadata_pipe_or_comma_tokens(raw: str) -> List[str]:
    """Split pipe- or comma-delimited metadata fields (``calls``, ``concepts``).

    Pipe-delimited format (``|a|b|c|``) is written by the ingestion pipeline.
    Comma-delimited is the legacy / human-authored form.  Both are accepted.
    """
    s = (raw or "").strip()
    if not s:
        return []
    if s.startswith("|"):
        return [x.strip() for x in s.strip("|").split("|") if x.strip()]
    return [x.strip() for x in s.split(",") if x.strip()]


def parse_dependency_tokens(deps: str) -> List[str]:
    """Parse the comma-delimited ``dependencies`` metadata field.

    Returns a de-duplicated, order-preserving list of non-empty tokens.
    """
    seen: set = set()
    out: List[str] = []
    for part in (deps or "").split(","):
        t = part.strip()
        if not t or t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out


# ---------------------------------------------------------------------------
# Dependency-hop helpers
# ---------------------------------------------------------------------------

def depend_stems_from_results(
    results: List[Tuple[Any, Optional[float], str]],
) -> List[str]:
    """Extract file stems and chunk_names from primary search results.

    Used to build the lookup set for the dependency second-pass hop.

    Parameters
    ----------
    results:
        List of ``(doc, score, source_type)`` tuples where *doc* has a
        ``.metadata`` dict.

    Returns
    -------
    Sorted, deduplicated list of stems / names.
    """
    stems: set = set()
    for doc, _, _ in results:
        meta = getattr(doc, "metadata", None) or {}
        rel = str(meta.get("relative_path") or "").strip()
        if rel:
            stems.add(Path(rel).stem)
            stems.add(Path(rel.replace("\\", "/")).name)
        cn = str(meta.get("chunk_name") or "").strip()
        if cn:
            stems.add(cn)
    return sorted(stems)


def dependencies_where_comma_token(stem: str) -> Dict[str, Any]:
    """Build a Chroma ``where`` filter that matches *stem* in the comma-delimited
    ``dependencies`` metadata field.

    Matches:
    - exact equality (single-entry field)
    - stem appears as the first entry  ``"stem, …"``
    - stem appears in the middle        ``"…, stem, …"``
    - stem appears as the last entry    ``"…, stem"``
    """
    s = (stem or "").strip()
    if not s:
        # Return a filter that can never match so callers don't have to special-case.
        return {"dependencies": {"$eq": "__empty_dependency_stem__"}}
    return {
        "$or": [
            {"dependencies": {"$eq": s}},
            {"dependencies": {"$contains": f"{s}, "}},
            {"dependencies": {"$contains": f", {s}, "}},
            {"dependencies": {"$contains": f", {s}"}},
        ]
    }


# ---------------------------------------------------------------------------
# iter_concept_ids — re-export so callers have one import location
# ---------------------------------------------------------------------------

def iter_concept_ids(concepts_field: str) -> List[str]:
    """Split the ``concepts`` metadata field into individual concept IDs.

    Pipe-delimited (``|id1|id2|``) or comma-delimited; matches ingest.py's
    ``iter_concept_ids`` exactly.  Re-exported here so mcp_server / query
    have a single import location.
    """
    return metadata_pipe_or_comma_tokens(concepts_field)
