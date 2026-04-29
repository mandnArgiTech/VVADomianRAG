"""Hybrid / dense retrieval, god-mode exact hits, dependency + caller hops."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import util.constants as uc

from hybrid_search import (
    HYBRID_AVAILABLE,
    get_bm25_index,
    reciprocal_rank_fusion,
    search_bm25_ranked_ids,
    stable_doc_id,
)
from langchain_core.documents import Document
from langchain_chroma import Chroma
from reranker import get_reranker, rerank_pool_limit

from util.constants import GOD_MODE_MIN_CONTENT_SIZE, HYBRID_SEARCH, RRF_K
from util.formatting import infer_source_type as _infer_source_type
from util.chunk_metadata import (
    depend_stems_from_results as _depend_stems_from_results,
    dependencies_where_comma_token as _dependencies_where_comma_token,
)
from util.search_primitives import (
    SearchHit,
    hybrid_candidate_cap as _hybrid_candidate_cap,
    select_collection_names as _select_collection_names,
    shared_query_embedding as _shared_query_embedding,
    similarity_search_with_score as _similarity_search_with_score_efficient,
)

from query_kit.god_mode import expand_query_typos, god_mode_chunk_name_matches, load_symbols_vocab

_LOG = logging.getLogger("query")


def resolve_db_abs(db_path: str, cmap: Dict[str, Chroma]) -> str:
    if db_path.strip():
        return os.path.abspath(db_path)
    for vs in cmap.values():
        pd = getattr(vs, "_persist_directory", None) or getattr(vs, "persist_directory", None)
        if pd:
            return os.path.abspath(str(pd))
    return ""


def exact_chunk_name_hits(
    query_raw: str,
    targets: List[str],
    cmap: Dict[str, Chroma],
    repo_filter: str,
    vocab: frozenset,
) -> List[SearchHit]:
    """Fast metadata pre-fetch: chunk_names from ``god_mode_chunk_name_matches``."""
    matches = god_mode_chunk_name_matches(query_raw, vocab)
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
            _LOG.debug("exact chunk_name lookup failed on %s: %s", name, exc)
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
            st = _infer_source_type(meta)
            meta["_exact_match"] = "chunk_name"
            exact.append(
                SearchHit(content=text, score=0.0, source_type=st, metadata=meta, collection=name)
            )
    return exact


def sync_multi_search(
    query: str,
    k: int,
    search_type: str,
    domain: str,
    repo_filter: str,
    cmap: Dict[str, Chroma],
    db_path: str = "",
    min_score_threshold: float = 0.0,
) -> List[SearchHit]:
    """Retrieve up to k chunks using dense or hybrid (RRF) search."""
    db_abs_for_vocab = resolve_db_abs(db_path, cmap)
    vocab = load_symbols_vocab(db_abs_for_vocab)
    query = expand_query_typos(query, vocab)
    if not cmap:
        raise RuntimeError("ChromaDB has no collections.")
    targets = _select_collection_names(cmap, search_type, domain)
    exact_hits = exact_chunk_name_hits(query, targets, cmap, repo_filter, vocab)
    exact_seen = {stable_doc_id(h.collection or "", h.metadata, h.content) for h in exact_hits}
    per = max(1, k // max(1, len(targets)) if targets else k)
    q_emb = _shared_query_embedding(cmap, targets, query)
    use_hybrid = HYBRID_SEARCH and HYBRID_AVAILABLE and bool(resolve_db_abs(db_path, cmap))
    if HYBRID_SEARCH and not HYBRID_AVAILABLE:
        _LOG.warning(
            "HYBRID_SEARCH is on but rank-bm25 is not installed; using dense-only. pip install rank-bm25"
        )

    def _hit(doc: Any, score: Optional[float], st: str, cname: str) -> SearchHit:
        return SearchHit(
            content=doc.page_content or "",
            score=float(score) if score is not None else None,
            source_type=st,
            metadata=dict(doc.metadata or {}),
            collection=cname,
        )

    if not use_hybrid:
        merged: List[Tuple[Any, Optional[float], str, str]] = []
        for name in targets:
            vs = cmap[name]
            flt: Optional[Dict[str, str]] = None
            if repo_filter.strip():
                flt = {"repository": repo_filter.strip()}
            try:
                pairs = _similarity_search_with_score_efficient(vs, query, per, flt, q_emb)
            except Exception as exc:
                _LOG.warning("Skipping collection %s: %s", name, exc)
                continue
            for doc, score in pairs:
                meta = doc.metadata or {}
                st = _infer_source_type(meta)
                if search_type.lower() == "troubleshoot":
                    ct = (meta.get("content_type") or "").lower()
                    if ct not in ("edge_case", "workaround", "bug_report"):
                        continue
                merged.append((doc, score, st, name))
        merged.sort(key=lambda x: x[1] if x[1] is not None else 1e9)
        if min_score_threshold > 0:
            merged = [(d, s, st, cn) for d, s, st, cn in merged if s is None or s <= min_score_threshold]
        regular = [
            _hit(doc, score, st, cn)
            for doc, score, st, cn in merged[: rerank_pool_limit(k)]
            if stable_doc_id(cn, doc.metadata or {}, doc.page_content) not in exact_seen
        ]
        _reranker = get_reranker()
        if _reranker is not None and regular:
            _cand_count = int(os.environ.get("RAG_RERANKER_CANDIDATES", "30"))
            _to_rerank = regular[:_cand_count]
            _texts = [h.content for h in _to_rerank]
            _ranked = _reranker.rerank(query, _texts, top_k=k)
            regular = [_to_rerank[idx] for idx, _score in _ranked]
        return exact_hits + regular

    db_abs = resolve_db_abs(db_path, cmap)
    dense_cap = _hybrid_candidate_cap(k, "HYBRID_DENSE_CANDIDATES")
    bm25_cap = _hybrid_candidate_cap(k, "HYBRID_BM25_CANDIDATES")
    fused: List[Tuple[Any, Optional[float], str, str, float]] = []

    for name in targets:
        vs = cmap[name]
        flt: Optional[Dict[str, str]] = None
        if repo_filter.strip():
            flt = {"repository": repo_filter.strip()}
        try:
            pairs = _similarity_search_with_score_efficient(vs, query, dense_cap, flt, q_emb)
        except Exception as exc:
            _LOG.warning("Skipping collection %s: %s", name, exc)
            continue

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
                bm25_ids = search_bm25_ranked_ids(idx, query, bm25_cap, repo_filter)
        rank_lists = [dense_ids, bm25_ids] if bm25_ids else [dense_ids]
        rrf_scores = reciprocal_rank_fusion(rank_lists, k=RRF_K)
        if not rrf_scores:
            continue

        bm25_rank = {sid: r for r, sid in enumerate(bm25_ids)}
        dense_rank = {sid: r for r, sid in enumerate(dense_ids)}
        sorted_sids = sorted(
            rrf_scores.keys(),
            key=lambda sid: (
                -rrf_scores[sid],
                bm25_rank.get(sid, 10**9),
                dense_rank.get(sid, 10**9),
            ),
        )
        idx_ref = get_bm25_index(db_abs, name) if col is not None else None
        for sid in sorted_sids:
            if sid in dense_map:
                doc, _dscore = dense_map[sid]
            elif idx_ref is not None and sid in idx_ref.id_to_doc:
                text, meta = idx_ref.id_to_doc[sid]
                doc = Document(page_content=text, metadata=meta)
            else:
                continue
            meta = doc.metadata or {}
            st = _infer_source_type(meta)
            if search_type.lower() == "troubleshoot":
                ct = (meta.get("content_type") or "").lower()
                if ct not in ("edge_case", "workaround", "bug_report"):
                    continue
            fused.append((doc, None, st, name, rrf_scores[sid]))

    fused.sort(key=lambda x: x[4], reverse=True)
    regular = [
        _hit(doc, score, st, cn)
        for doc, score, st, cn, _ in fused[: rerank_pool_limit(k)]
        if stable_doc_id(cn, doc.metadata or {}, doc.page_content) not in exact_seen
    ]
    _reranker = get_reranker()
    if _reranker is not None and regular:
        _cand_count = int(os.environ.get("RAG_RERANKER_CANDIDATES", "30"))
        _to_rerank = regular[:_cand_count]
        _texts = [h.content for h in _to_rerank]
        _ranked = _reranker.rerank(query, _texts, top_k=k)
        regular = [_to_rerank[idx] for idx, _score in _ranked]
    return exact_hits + regular


def fused_docs_for_query_text(
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
    """Dense or hybrid (RRF) retrieval for a single query string in one collection."""
    if k_out <= 0:
        return []
    flt: Optional[Dict[str, str]] = None
    if repo_filter.strip():
        flt = {"repository": repo_filter.strip()}
    q_emb = _shared_query_embedding(cmap, [name], query_text)

    def _passes_tt(meta: Dict[str, Any]) -> bool:
        if skip_troubleshoot_gate or search_type.lower() != "troubleshoot":
            return True
        ct = (meta.get("content_type") or "").lower()
        return ct in ("edge_case", "workaround", "bug_report")

    if not use_hybrid:
        pairs = _similarity_search_with_score_efficient(
            vs, query_text, max(k_out * 3, 8), flt, q_emb
        )
        out: List[Tuple[Any, Optional[float]]] = []
        for doc, score in pairs:
            if not _passes_tt(doc.metadata or {}):
                continue
            out.append((doc, float(score) if score is not None else None))
            if len(out) >= k_out:
                break
        return out

    dense_cap = _hybrid_candidate_cap(max(k_out, 4), "HYBRID_DENSE_CANDIDATES")
    bm25_cap = _hybrid_candidate_cap(max(k_out, 4), "HYBRID_BM25_CANDIDATES")
    pairs = _similarity_search_with_score_efficient(vs, query_text, dense_cap, flt, q_emb)
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


def sync_fetch_dependents(
    primary: List[Tuple[Any, Optional[float], str]],
    search_type: str,
    domain: str,
    repo_filter: str,
    cmap: Dict[str, Chroma],
    max_hits: int,
) -> List[Tuple[Any, Optional[float], str, str]]:
    targets = _select_collection_names(cmap, search_type, domain)
    lookups = _depend_stems_from_results(primary)
    if not lookups or not targets:
        return []
    seen: set = set()
    out: List[Tuple[Any, Optional[float], str, str]] = []
    rf = repo_filter.strip()
    for stem in lookups:
        if not stem:
            continue
        where_dep = _dependencies_where_comma_token(stem)
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
                _LOG.warning("dependents get failed on %s: %s", name, exc)
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
                st = _infer_source_type(meta or {})
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
    code_names = _select_collection_names(cmap, search_type, domain)
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
                _LOG.warning("caller get failed on %s: %s", coll_name, exc)
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
                st = _infer_source_type(meta or {})
                out.append((doc, None, st, coll_name))
                if len(out) >= max_hits:
                    return out
    return out


def sync_multi_search_with_dependency_hop(
    query: str,
    k: int,
    search_type: str,
    domain: str,
    repo_filter: str,
    cmap: Dict[str, Chroma],
    db_path: str = "",
    min_score_threshold: float = 0.0,
) -> List[SearchHit]:
    """Primary search plus Chroma ``dependencies`` metadata lookup."""
    primary = sync_multi_search(
        query, k, search_type, domain, repo_filter, cmap, db_path, min_score_threshold
    )
    if uc.QUERY_DEP_MAX_HITS <= 0 or not primary:
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
        max_hits=min(k * 2, max(1, uc.QUERY_DEP_MAX_HITS * 2)),
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

    if uc.QUERY_CALLER_MAX_HITS > 0:
        caller_tuples = sync_fetch_callers(
            primary,
            search_type,
            domain,
            repo_filter,
            cmap,
            max_hits=uc.QUERY_CALLER_MAX_HITS,
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


# Historical underscored names (compat)
_resolve_db_abs = resolve_db_abs
_exact_chunk_name_hits = exact_chunk_name_hits
_sync_multi_search = sync_multi_search
_fused_docs_for_query_text = fused_docs_for_query_text
_sync_fetch_dependents = sync_fetch_dependents
_sync_fetch_callers = sync_fetch_callers
_sync_multi_search_with_dependency_hop = sync_multi_search_with_dependency_hop
