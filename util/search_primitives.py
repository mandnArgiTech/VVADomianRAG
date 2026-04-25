"""util/search_primitives.py — Stateless search building blocks."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from langchain_chroma import Chroma

from util.constants import RAG_QUERY_SHARED_EMBED

_log = logging.getLogger(__name__)


@dataclass
class SearchHit:
    content: str
    score: Optional[float]
    source_type: str
    metadata: Dict[str, Any]
    collection: Optional[str] = None
    retrieval_hop: Optional[str] = None


def domain_filter(names: List[str], domain: str) -> List[str]:
    d = domain.strip().lower()
    if not d or d == "general":
        return names
    return [n for n in names if n.lower().startswith(d + "_") or n.lower() == d]


def select_collection_names(cmap: Dict[str, Chroma], search_type: str, domain: str) -> List[str]:
    names = list(cmap.keys())
    names = domain_filter(names, domain)
    st = search_type.lower().strip()
    if st == "auto" or not st:
        return names
    if st == "code":
        return [n for n in names if n.endswith("_code")]
    if st == "domain":
        return [n for n in names if "_domain" in n or n == "theory"]
    if st == "troubleshoot":
        return [
            n
            for n in names
            if any(x in n for x in ("_domain", "community", "_customer", "_internal"))
        ]
    if st == "reference":
        return [n for n in names if n == "rfc" or n == "theory" or "_mib" in n or n.endswith("_releases")]
    return names


def hybrid_candidate_cap(k: int, env_var: str) -> int:
    raw = os.environ.get(env_var, "").strip()
    if raw.isdigit():
        return max(1, int(raw))
    return max(40, k * 4)


def shared_query_embedding(
    cmap: Dict[str, Chroma], targets: List[str], query: str
) -> Optional[List[float]]:
    """Single embed_query for all collections (same model / vector space)."""
    if not RAG_QUERY_SHARED_EMBED or not targets or not (query or "").strip():
        return None
    vs0 = cmap.get(targets[0])
    if vs0 is None:
        return None
    emb_fn = getattr(vs0, "_embedding_function", None)
    if emb_fn is None:
        return None
    try:
        vec = emb_fn.embed_query(query)
        return list(vec) if vec is not None else None
    except Exception as exc:
        _log.debug("shared embed_query failed, using per-query embedding: %s", exc)
        return None


def similarity_search_with_score(
    vs: Any,
    query: str,
    k: int,
    flt: Optional[Dict[str, str]],
    q_emb: Optional[List[float]],
) -> List[Tuple[Any, Any]]:
    """Dense search: reuse precomputed embedding when LangChain Chroma supports it."""
    if q_emb is not None:
        fn = getattr(vs, "similarity_search_by_vector_with_relevance_scores", None)
        if callable(fn):
            try:
                return fn(q_emb, k=k, filter=flt)
            except TypeError:
                try:
                    return fn(q_emb, k, flt)
                except Exception:
                    pass
            except Exception as exc:
                _log.debug("similarity_search_by_vector_with_relevance_scores failed: %s", exc)
    try:
        if flt is not None:
            return vs.similarity_search_with_score(query, k=k, filter=flt)
        return vs.similarity_search_with_score(query, k=k)
    except TypeError:
        return vs.similarity_search_with_score(query, k=k)
