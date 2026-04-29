"""Concept-ID retrieval via Chroma ``concepts`` metadata."""

from __future__ import annotations

import logging
from typing import Dict, List

from langchain_chroma import Chroma

from util.formatting import infer_source_type as _infer_source_type
from util.search_primitives import SearchHit, domain_filter as _domain_filter

_LOG = logging.getLogger("query")


def concept_parts(concepts_field: str) -> List[str]:
    s = (concepts_field or "").strip()
    if not s:
        return []
    if s.startswith("|"):
        return [x.strip() for x in s.strip("|").split("|") if x.strip()]
    return [x.strip() for x in s.split(",") if x.strip()]


def concept_search_hits(concept: str, domain: str, cmap: Dict[str, Chroma]) -> List[SearchHit]:
    concept = concept.strip()
    if not concept:
        return []
    safe_concept = concept.replace("|", "")
    if not safe_concept:
        return []
    needle = f"|{safe_concept}|"
    hits: List[SearchHit] = []
    for cname, vs in cmap.items():
        if domain and not _domain_filter([cname], domain):
            continue
        try:
            col = vs._collection  # type: ignore[attr-defined]
            res = col.get(
                where={"concepts": {"$contains": needle}},
                limit=80,
                include=["documents", "metadatas"],
            )
            if not (res.get("ids") or []):
                res = col.get(
                    where={"concepts": {"$contains": safe_concept}},
                    limit=80,
                    include=["documents", "metadatas"],
                )
            ids_list = res.get("ids") or []
            docs = res.get("documents") or []
            metas = res.get("metadatas") or []
            for i, _did in enumerate(ids_list):
                text = docs[i] if i < len(docs) else ""
                meta = metas[i] if i < len(metas) else {}
                st = _infer_source_type(meta or {})
                hits.append(
                    SearchHit(
                        content=text or "",
                        score=None,
                        source_type=st,
                        metadata=dict(meta or {}),
                        collection=cname,
                    )
                )
        except Exception as exc:
            _LOG.warning("concept query failed on %s: %s", cname, exc)
    return hits


_concept_parts = concept_parts
