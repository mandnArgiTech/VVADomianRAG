"""
util/search_core.py — Collection routing, dense/hybrid search, dependency hops.

Previously duplicated across query.py and mcp_server.py.  Both callers import
from here; neither carries its own copy any longer.

The implementation is the merged authoritative version:
- mcp_server's callee-expand path (``_sync_fetch_callees``) lives in mcp_server
  because it owns the callee-expand toggle and executor.
- All other shared search logic lives here.

Public API
----------
SearchHit                                   dataclass
domain_filter(names, domain)                List[str]
select_collection_names(cmap, search_type, domain) List[str]
hybrid_candidate_cap(k, env_var)            int
shared_query_embedding(cmap, targets, query) Optional[List[float]]
similarity_search_with_score(vs, query, k, flt, q_emb) List[Tuple[doc, score]]
exact_chunk_name_hits(...)                  List[SearchHit]
sync_multi_search(...)                      List[SearchHit]
sync_fetch_dependents(...)                  List[Tuple[doc, score, st, coll]]
sync_fetch_callers(...)                     List[Tuple[doc, score, st, coll]]
sync_multi_search_with_dependency_hop(...)  List[SearchHit]
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from langchain_chroma import Chroma
from langchain_core.documents import Document

from hybrid_search import (
    get_bm25_index,
    reciprocal_rank_fusion,
    search_bm25_ranked_ids,
    stable_doc_id,
)
from util.chunk_metadata import (
    depend_stems_from_results,
    dependencies_where_comma_token,
    metadata_pipe_or_comma_tokens,
)
from util.formatting import infer_source_type

__all__ = [
    "SearchHit",
    "domain_filter",
    "select_collection_names",
    "hybrid_candidate_cap",
    "shared_query_embedding",
    "similarity_search_with_score",
    "exact_chunk_name_hits",
    "sync_multi_search",
    "sync_fetch_dependents",
    "sync_fetch_callers",
    "sync_multi_search_with_dependency_hop",
]

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Env-driven search parameters
# ---------------------------------------------------------------------------

HYBRID_SEARCH = os.environ.get("HYBRID_SEARCH", "1").strip().lower() not in ("0", "false", "no")
RRF_K = float(os.environ.get("RRF_K", "60"))
RAG_QUERY_SHARED_EMBED = os.environ.get("RAG_QUERY_SHARED_EMBED", "1").strip().lower() not in (
    "0", "false", "no",
)
QUERY_DEP_MAX_HITS = max(0, int(os.environ.get("QUERY_DEP_MAX_HITS", "10")))
QUERY_DEP_LOOKUP_K = max(1, int(os.environ.get("QUERY_DEP_LOOKUP_K", "2")))
QUERY_CALLER_MAX_HITS = max(0, int(os.environ.get("QUERY_CALLER_MAX_HITS", "10")))

# God-mode minimum: drop tiny declaration chunks
GOD_MODE_MIN_CONTENT_SIZE = 50


# ---------------------------------------------------------------------------
# SearchHit — universal retrieval result
# ---------------------------------------------------------------------------

@dataclass
class SearchHit:
    """Single ranked retrieval result from any search path."""

    content: str
    score: Optional[float]
    source_type: str
    metadata: Dict[str, Any]
    collection: Optional[str] = None
    retrieval_hop: Optional[str] = None


# ---------------------------------------------------------------------------
# Collection routing
# ---------------------------------------------------------------------------

def domain_filter(names: List[str], domain: str) -> List[str]:
    """Keep only collection names matching *domain* (prefix or exact)."""
    d = domain.strip().lower()
    if not d or d == "general":
        return names
    return [n for n in names if n.lower().startswith(d + "_") or n.lower() == d]


def select_collection_names(
    cmap: Dict[str, Chroma],
    search_type: str,
    domain: str,
) -> List[str]:
    """Return the ordered list of collection names relevant to this search."""
    names = domain_filter(list(cmap.keys()), domain)
    st = search_type.lower().strip()
    if st == "auto" or not st:
        return names
    if st == "code":
        return [n for n in names if n.endswith("_code")]
    if st == "domain":
        return [n for n in names if "_domain" in n or n == "theory"]
    if st in ("troubleshoot", "reference"):
        return names
    return names


def hybrid_candidate_cap(k: int, env_var: str) -> int:
    """Compute over-fetch pool size from env var or fallback heuristic."""
    raw = os.environ.get(env_var, "").strip()
    if raw.isdigit():
        return max(1, int(raw))
    return max(40, k * 4)


# ---------------------------------------------------------------------------
# Embedding helpers
# ---------------------------------------------------------------------------

def shared_query_embedding(
    cmap: Dict[str, Chroma],
    targets: List[str],
    query: str,
) -> Optional[List[float]]:
    """Compute a single embedding for *query* reused across all collections.

    Returns None when disabled, when targets is empty, or on any error.
    """
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
        log.debug("shared embed_query failed, using per-query embedding: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Dense search wrapper
# ---------------------------------------------------------------------------

def similarity_search_with_score(
    vs: Any,
    query: str,
    k: int,
    flt: Optional[Dict[str, str]],
    q_emb: Optional[List[float]],
) -> List[Tuple[Any, Any]]:
    """Dense vector search; reuses pre-computed embedding when supported."""
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
                log.debug("similarity_search_by_vector_with_relevance_scores failed: %s", exc)
    try:
        if flt is not None:
            return vs.similarity_search_with_score(query, k=k, filter=flt)
        return vs.similarity_search_with_score(query, k=k)
    except TypeError:
        return vs.similarity_search_with_score(query, k=k)


# ---------------------------------------------------------------------------
# Exact chunk-name (god-mode) hits
# ---------------------------------------------------------------------------

def exact_chunk_name_hits(
    query_raw: str,
    targets: List[str],
    cmap: Dict[str, Chroma],
    repo_filter: str,
    vocab: frozenset,
    god_mode_chunk_name_matches_fn: Any,
) -> List[SearchHit]:
    """Fast metadata pre-fetch: match chunk_names exactly.

    Parameters
    ----------
    god_mode_chunk_name_matches_fn:
        Callable(query_raw, vocab) → List[str].  Passed explicitly so this
        module does not import query-specific god-mode logic.
    """
    matches = god_mode_chunk_name_matches_fn(query_raw, vocab)
    if not matches:
        return []
    chroma_limit = min(512, max(8, len(matches) * 8))
    exact: List[SearchHit] = []
    seen: set = set()
    rf = repo_filter.strip()
    for name in targets:
        vs = cmap.get(name)
        if vs is None:
            continue
        col = getattr(vs, "_collection", None)
        if col is None:
            continue
        try:
            res = col.get(
                where={"chunk_name": {"$in": matches}},
                limit=chroma_limit,
                include=["documents", "metadatas"],
            )
        except Exception as exc:
            log.debug("exact chunk_name lookup failed on %s: %s", name, exc)
            continue
        docs = res.get("documents") or []
        metas = res.get("metadatas") or []
        ids_list = res.get("ids") or []
        for i in range(len(docs)):
            text = docs[i] if i < len(docs) else ""
            if len((text or "").strip()) < GOD_MODE_MIN_CONTENT_SIZE:
                continue
            meta = dict(metas[i] if i < len(metas) else {})
            did = ids_list[i] if i < len(ids_list) else ""
            key = did or stable_doc_id(name, meta, text)
            if key in seen:
                continue
            if rf and str(meta.get("repository", "")).strip() != rf:
                continue
            seen.add(key)
            st = infer_source_type(meta)
            meta["_exact_match"] = "chunk_name"
            exact.append(
                SearchHit(content=text, score=0.0, source_type=st, metadata=meta, collection=name)
            )
    return exact


# ---------------------------------------------------------------------------
# Dense + hybrid multi-collection search
# ---------------------------------------------------------------------------

def _fused_docs_for_query(
    name: str,
    vs: Any,
    query_text: str,
    db_abs: str,
    repo_filter: str,
    search_type: str,
    cmap: Dict[str, Chroma],
    k_out: int,
    use_hybrid: bool,
    *,
    skip_troubleshoot_gate: bool = False,
) -> List[Tuple[Any, Optional[float]]]:
    """Dense or hybrid (RRF) retrieval for a single query in one collection."""
    if k_out <= 0:
        return []
    flt: Optional[Dict[str, str]] = None
    if repo_filter.strip():
        flt = {"repository": repo_filter.strip()}
    q_emb = shared_query_embedding(cmap, [name], query_text)

    def _passes_tt(meta: Dict[str, Any]) -> bool:
        if skip_troubleshoot_gate or search_type.lower() != "troubleshoot":
            return True
        ct = (meta.get("content_type") or "").lower()
        return ct in ("edge_case", "workaround", "bug_report")

    if not use_hybrid:
        pairs = similarity_search_with_score(vs, query_text, max(k_out * 3, 8), flt, q_emb)
        out: List[Tuple[Any, Optional[float]]] = []
        for doc, score in pairs:
            if not _passes_tt(doc.metadata or {}):
                continue
            out.append((doc, float(score) if score is not None else None))
            if len(out) >= k_out:
                break
        return out

    dense_cap = hybrid_candidate_cap(max(k_out, 4), "HYBRID_DENSE_CANDIDATES")
    bm25_cap = hybrid_candidate_cap(max(k_out, 4), "HYBRID_BM25_CANDIDATES")
    pairs = similarity_search_with_score(vs, query_text, dense_cap, flt, q_emb)
    dense_ids: List[str] = []
    dense_map: Dict[str, Tuple[Any, float]] = {}
    for doc, score in pairs:
        sid = stable_doc_id(name, doc.metadata or {}, doc.page_content)
        dense_ids.append(sid)
        dense_map[sid] = (doc, score)

    bm25_ids: List[str] = []
    col = getattr(vs, "_collection", None)
    if col is not None and db_abs:
        idx = get_bm25_index(db_abs, name)
        if idx.ensure_loaded(col):
            bm25_ids = search_bm25_ranked_ids(idx, query_text, bm25_cap, repo_filter)

    rank_lists = [dense_ids, bm25_ids] if bm25_ids else [dense_ids]
    rrf_scores = reciprocal_rank_fusion(rank_lists, k=RRF_K)
    if not rrf_scores:
        return []
    sorted_sids = sorted(rrf_scores.keys(), key=lambda sid: -rrf_scores[sid])
    idx_ref = get_bm25_index(db_abs, name) if col is not None else None
    out2: List[Tuple[Any, Optional[float]]] = []
    for sid in sorted_sids:
        if sid in dense_map:
            doc, sc = dense_map[sid]
        elif idx_ref is not None and sid in idx_ref.id_to_doc:
            text, meta = idx_ref.id_to_doc[sid]
            doc = Document(page_content=text, metadata=meta)
            sc = None
        else:
            continue
        if not _passes_tt(doc.metadata or {}):
            continue
        out2.append((doc, float(sc) if sc is not None else None))
        if len(out2) >= k_out:
            break
    return out2


def sync_multi_search(
    query: str,
    k: int,
    search_type: str,
    domain: str,
    repo_filter: str,
    cmap: Dict[str, Chroma],
    db_path: str = "",
    min_score_threshold: float = 0.0,
    *,
    result_chunk_max_chars: Optional[int] = None,
    result_context_window_max_chars: Optional[int] = None,
    exact_hits_fn: Optional[Any] = None,
) -> List[SearchHit]:
    """Retrieve up to *k* chunks using dense or hybrid (BM25 + RRF) search.

    Parameters
    ----------
    min_score_threshold:
        For dense-only mode, discard hits whose cosine-distance score exceeds
        this value.  0.0 disables the filter.
    exact_hits_fn:
        Optional Callable() → List[SearchHit] for god-mode exact chunk_name
        pre-fetch.  When provided, its results are prepended and their IDs
        excluded from the dense/hybrid pass.
    """
    from util.formatting import infer_source_type  # local to avoid circular

    targets = select_collection_names(cmap, search_type, domain)
    if not targets:
        return []

    # Resolve db_path from cmap when not provided
    db_abs = db_path.strip()
    if not db_abs:
        for vs in cmap.values():
            col = getattr(vs, "_collection", None)
            if col is not None:
                client = getattr(col, "_client", None)
                if client is not None:
                    try:
                        db_abs = str(getattr(client, "_path", "") or "")
                    except Exception:
                        pass
            if db_abs:
                break

    use_hybrid = HYBRID_SEARCH

    # Pre-fetch exact hits
    exact_hits: List[SearchHit] = []
    if exact_hits_fn is not None:
        exact_hits = exact_hits_fn()
    exact_seen = {
        stable_doc_id(h.collection or "", h.metadata, h.content)
        for h in exact_hits
    }

    pool_k = k
    from reranker import rerank_pool_limit  # lazy import
    pool_k = rerank_pool_limit(k)
    if exact_hits:
        pool_k = max(pool_k, k)

    q_emb_global = shared_query_embedding(cmap, targets, query)

    scored: List[Tuple[Any, Optional[float], str, str]] = []
    rf = repo_filter.strip()

    for name in targets:
        vs = cmap.get(name)
        if vs is None:
            continue
        pairs = _fused_docs_for_query(
            name, vs, query, db_abs, repo_filter, search_type, cmap, pool_k, use_hybrid
        )
        for doc, sc in pairs:
            meta = doc.metadata or {}
            sid = stable_doc_id(name, meta, doc.page_content)
            if sid in exact_seen:
                continue
            if rf and str(meta.get("repository", "")).strip() != rf:
                continue
            if min_score_threshold > 0 and sc is not None and not use_hybrid:
                if sc > min_score_threshold:
                    continue
            st = infer_source_type(meta)
            scored.append((doc, sc, st, name))

    # Sort by score (ascending = closer)
    scored.sort(key=lambda t: (t[1] is None, t[1] if t[1] is not None else 0.0))
    scored = scored[:pool_k]

    # Optional reranking
    from reranker import get_reranker
    reranker = get_reranker()
    if reranker is not None and scored:
        texts = [(doc.page_content or "") for doc, _, _, _ in scored]
        ranked = reranker.rerank(query, texts, top_k=k)
        scored = [scored[i] for i, _ in ranked]
    else:
        scored = scored[:k]

    hits: List[SearchHit] = list(exact_hits)
    seen = set(exact_seen)
    for doc, sc, st, name in scored:
        meta = dict(doc.metadata or {})
        sid = stable_doc_id(name, meta, doc.page_content)
        if sid in seen:
            continue
        seen.add(sid)
        hits.append(
            SearchHit(
                content=doc.page_content or "",
                score=float(sc) if sc is not None else None,
                source_type=st,
                metadata=meta,
                collection=name,
            )
        )

    return hits[:k + len(exact_hits)]


# ---------------------------------------------------------------------------
# Dependency second-pass hop
# ---------------------------------------------------------------------------

def sync_fetch_dependents(
    primary: List[Tuple[Any, Optional[float], str]],
    search_type: str,
    domain: str,
    repo_filter: str,
    cmap: Dict[str, Chroma],
    max_hits: int,
) -> List[Tuple[Any, Optional[float], str, str]]:
    """Fetch chunks whose ``dependencies`` metadata references primary hit symbols.

    Returns ``(doc, score, source_type, collection_name)`` tuples for stable
    deduplication / SearchHit construction.
    """
    targets = select_collection_names(cmap, search_type, domain)
    lookups = depend_stems_from_results(primary)
    if not lookups or not targets:
        return []
    seen: set = set()
    out: List[Tuple[Any, Optional[float], str, str]] = []
    rf = repo_filter.strip()
    for stem in lookups:
        if not stem:
            continue
        where_dep = dependencies_where_comma_token(stem)
        for name in targets:
            vs = cmap[name]
            col = getattr(vs, "_collection", None)
            if col is None:
                continue
            try:
                res = col.get(
                    where=where_dep,
                    limit=40,
                    include=["documents", "metadatas"],
                )
            except Exception as exc:
                log.warning("dependents get failed on %s: %s", name, exc)
                continue
            ids_list = res.get("ids") or []
            docs = res.get("documents") or []
            metas = res.get("metadatas") or []
            for i, did in enumerate(ids_list):
                if did in seen:
                    continue
                meta = metas[i] if i < len(metas) else {}
                if rf and str((meta or {}).get("repository", "")).strip() != rf:
                    continue
                seen.add(did)
                text = docs[i] if i < len(docs) else ""
                doc = Document(page_content=text or "", metadata=dict(meta or {}))
                st = infer_source_type(meta or {})
                out.append((doc, None, st, name))
                if len(out) >= max_hits:
                    return out
    return out


def sync_fetch_callers(
    primary: List[SearchHit],
    search_type: str,
    domain: str,
    repo_filter: str,
    cmap: Dict[str, Chroma],
    max_hits: int,
) -> List[Tuple[Any, Optional[float], str, str]]:
    """Fetch chunks that call functions found in primary hits (reverse call-graph).

    For each primary code hit with a ``chunk_name``, queries code collections
    for chunks whose ``calls`` metadata contains ``|chunk_name|``.

    Returns ``(doc, score, source_type, collection_name)`` tuples.
    """
    code_names = select_collection_names(cmap, search_type, domain)
    rf = repo_filter.strip()
    seen: set = set()
    out: List[Tuple[Any, Optional[float], str, str]] = []
    for hit in primary:
        if hit.source_type != "code":
            continue
        chunk_name = str((hit.metadata or {}).get("chunk_name") or "").strip()
        if not chunk_name:
            continue
        needle = f"|{chunk_name}|"
        for coll_name in code_names:
            if len(out) >= max_hits:
                return out
            vs = cmap[coll_name]
            col = getattr(vs, "_collection", None)
            if col is None:
                continue
            try:
                res = col.get(
                    where={"calls": {"$contains": needle}},
                    limit=5,
                    include=["documents", "metadatas"],
                )
            except Exception as exc:
                log.warning("caller get failed on %s: %s", coll_name, exc)
                continue
            ids_list = res.get("ids") or []
            docs_list = res.get("documents") or []
            metas_list = res.get("metadatas") or []
            for i, did in enumerate(ids_list):
                if did in seen:
                    continue
                meta = metas_list[i] if i < len(metas_list) else {}
                if rf and str((meta or {}).get("repository", "")).strip() != rf:
                    continue
                seen.add(did)
                text = docs_list[i] if i < len(docs_list) else ""
                doc = Document(page_content=text or "", metadata=dict(meta or {}))
                st = infer_source_type(meta or {})
                out.append((doc, None, st, coll_name))
                if len(out) >= max_hits:
                    return out
    return out


# ---------------------------------------------------------------------------
# Full pipeline: primary + dependency + caller hops
# ---------------------------------------------------------------------------

def sync_multi_search_with_dependency_hop(
    query: str,
    k: int,
    search_type: str,
    domain: str,
    repo_filter: str,
    cmap: Dict[str, Chroma],
    db_path: str = "",
    min_score_threshold: float = 0.0,
    *,
    result_chunk_max_chars: Optional[int] = None,
    result_context_window_max_chars: Optional[int] = None,
    exact_hits_fn: Optional[Any] = None,
) -> List[SearchHit]:
    """Primary search + dependency-metadata lookup + caller reverse-hop.

    This is the top-level retrieval entry point used by both query.py and
    mcp_server.py.
    """
    primary = sync_multi_search(
        query, k, search_type, domain, repo_filter, cmap, db_path,
        min_score_threshold,
        result_chunk_max_chars=result_chunk_max_chars,
        result_context_window_max_chars=result_context_window_max_chars,
        exact_hits_fn=exact_hits_fn,
    )
    if QUERY_DEP_MAX_HITS <= 0 or not primary:
        return primary

    primary_tuples: List[Tuple[Any, Optional[float], str]] = [
        (Document(page_content=h.content, metadata=dict(h.metadata or {})), h.score, h.source_type)
        for h in primary
    ]
    dep_tuples = sync_fetch_dependents(
        primary_tuples,
        search_type,
        domain,
        repo_filter,
        cmap,
        max_hits=min(k * 2, max(1, QUERY_DEP_MAX_HITS * 2)),
    )
    seen = {stable_doc_id(h.collection or "", h.metadata, h.content) for h in primary}
    extra: List[SearchHit] = []
    for doc, _sc, st, cname in dep_tuples:
        sid = stable_doc_id(cname, doc.metadata or {}, doc.page_content or "")
        if sid in seen:
            continue
        seen.add(sid)
        meta = dict(doc.metadata or {})
        meta["retrieval_hop"] = "dependency"
        extra.append(
            SearchHit(
                content=doc.page_content or "",
                score=None,
                source_type=st,
                metadata=meta,
                collection=cname,
                retrieval_hop="dependency",
            )
        )

    if QUERY_CALLER_MAX_HITS > 0:
        caller_tuples = sync_fetch_callers(
            primary,
            search_type,
            domain,
            repo_filter,
            cmap,
            max_hits=QUERY_CALLER_MAX_HITS,
        )
        for doc, _sc, st, cname in caller_tuples:
            sid = stable_doc_id(cname, doc.metadata or {}, doc.page_content or "")
            if sid in seen:
                continue
            seen.add(sid)
            meta = dict(doc.metadata or {})
            meta["retrieval_hop"] = "caller"
            extra.append(
                SearchHit(
                    content=doc.page_content or "",
                    score=None,
                    source_type=st,
                    metadata=meta,
                    collection=cname,
                    retrieval_hop="caller",
                )
            )

    return primary + extra
