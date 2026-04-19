"""STORY E: Cross-encoder reranker — unit tests (RR-01 through RR-13).

All tests are fully mocked: no GPU, no model download required.
"""

from __future__ import annotations

import os
import sys
import types
from typing import Any, List
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fresh_reranker_module():
    """Reload reranker module to reset the module-level singleton."""
    import importlib
    import reranker as _mod
    _mod._instance = None
    return _mod


# ---------------------------------------------------------------------------
# RR-01: get_reranker returns None when RAG_RERANKER=0
# ---------------------------------------------------------------------------

def test_rr01_get_reranker_disabled(monkeypatch):
    monkeypatch.setenv("RAG_RERANKER", "0")
    mod = _fresh_reranker_module()
    assert mod.get_reranker() is None


# ---------------------------------------------------------------------------
# RR-02: get_reranker returns Reranker when RAG_RERANKER=1
# ---------------------------------------------------------------------------

def test_rr02_get_reranker_enabled(monkeypatch):
    monkeypatch.setenv("RAG_RERANKER", "1")
    monkeypatch.setenv("RAG_RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")
    mod = _fresh_reranker_module()
    r = mod.get_reranker()
    assert r is not None
    assert isinstance(r, mod.Reranker)


# ---------------------------------------------------------------------------
# RR-03: rerank returns correct ordering
# ---------------------------------------------------------------------------

def test_rr03_rerank_ordering():
    import reranker as mod
    r = mod.Reranker.__new__(mod.Reranker)
    r.model_name = "test"
    r.device = "cpu"
    r.use_fp16 = False

    mock_model = MagicMock()
    mock_model.predict.return_value = [0.1, 0.9, 0.5]
    r._model = mock_model

    result = r.rerank("q", ["doc0", "doc1", "doc2"])
    indices = [idx for idx, _score in result]
    assert indices == [1, 2, 0]


# ---------------------------------------------------------------------------
# RR-04: rerank respects top_k
# ---------------------------------------------------------------------------

def test_rr04_rerank_top_k():
    import reranker as mod
    r = mod.Reranker.__new__(mod.Reranker)
    r.model_name = "test"
    r.device = "cpu"
    r.use_fp16 = False

    mock_model = MagicMock()
    mock_model.predict.return_value = [0.5, 0.1, 0.8, 0.3, 0.9]
    r._model = mock_model

    result = r.rerank("q", ["d0", "d1", "d2", "d3", "d4"], top_k=2)
    assert len(result) == 2


# ---------------------------------------------------------------------------
# RR-05: rerank passthrough when _model is None
# ---------------------------------------------------------------------------

def test_rr05_passthrough_when_model_none():
    import reranker as mod
    r = mod.Reranker.__new__(mod.Reranker)
    r.model_name = "test"
    r.device = "cpu"
    r.use_fp16 = False
    r._model = None

    result = r.rerank("q", ["a", "b", "c"])
    assert result == [(0, 0.0), (1, 0.0), (2, 0.0)]


# ---------------------------------------------------------------------------
# RR-06: Lazy loading — _model is None at __init__
# ---------------------------------------------------------------------------

def test_rr06_lazy_model_none_at_init():
    import reranker as mod
    r = mod.Reranker(model_name="x", device="cpu", use_fp16=False)
    assert r._model is None


# ---------------------------------------------------------------------------
# RR-07: Lazy loading — model loaded on first rerank()
# ---------------------------------------------------------------------------

def test_rr07_lazy_model_loaded_on_rerank(monkeypatch):
    import reranker as mod

    mock_ce = MagicMock()
    mock_ce_instance = MagicMock()
    mock_ce_instance.predict.return_value = [0.5]
    mock_ce_instance.model = MagicMock()
    mock_ce.return_value = mock_ce_instance

    mock_torch = MagicMock()
    mock_torch.cuda.is_available.return_value = False

    mock_st = types.ModuleType("sentence_transformers")
    mock_st.CrossEncoder = mock_ce
    monkeypatch.setitem(sys.modules, "sentence_transformers", mock_st)
    monkeypatch.setitem(sys.modules, "torch", mock_torch)

    r = mod.Reranker(model_name="x", device="cpu", use_fp16=False)
    assert r._model is None
    r.rerank("q", ["doc"])
    assert r._model is not None


# ---------------------------------------------------------------------------
# RR-08: Singleton — get_reranker returns the same object
# ---------------------------------------------------------------------------

def test_rr08_singleton(monkeypatch):
    monkeypatch.setenv("RAG_RERANKER", "1")
    mod = _fresh_reranker_module()
    r1 = mod.get_reranker()
    r2 = mod.get_reranker()
    assert r1 is r2


# ---------------------------------------------------------------------------
# RR-09: Graceful degradation when sentence-transformers missing
# ---------------------------------------------------------------------------

def test_rr09_graceful_degradation_import_error(monkeypatch, caplog):
    import reranker as mod
    import logging

    r = mod.Reranker(model_name="x", device="cpu", use_fp16=False)

    def _raise(*a, **kw):
        raise ImportError("no sentence_transformers")

    with patch.dict(sys.modules, {"sentence_transformers": None}):
        with caplog.at_level(logging.WARNING, logger="reranker"):
            r._ensure_loaded()

    assert r._model is None
    assert any(
        "Reranker enabled but sentence-transformers not installed. "
        "pip install sentence-transformers. Falling back to RRF/dense scoring."
        in rec.getMessage()
        for rec in caplog.records
    )
    result = r.rerank("q", ["a", "b"])
    assert result == [(0, 0.0), (1, 0.0)]


# ---------------------------------------------------------------------------
# RR-10: mcp_server._sync_multi_search applies reranker (reverses order)
# ---------------------------------------------------------------------------

def _make_fake_doc(text: str, meta: dict = None):
    doc = MagicMock()
    doc.page_content = text
    doc.metadata = meta or {}
    return doc


def test_rr10_mcp_sync_multi_search_applies_reranker(monkeypatch):
    import mcp_server

    doc_a = _make_fake_doc("aaa")
    doc_b = _make_fake_doc("bbb")

    def fake_select(cmap, st, domain):
        return ["col"]

    def fake_exact(query, targets, cmap, repo_filter, vocab):
        return []

    def fake_dedup(doc):
        return doc.page_content

    def fake_load_vocab(db_path):
        return frozenset()

    fake_vs = MagicMock()
    fake_vs.similarity_search_with_score.return_value = [
        (doc_a, 0.1),
        (doc_b, 0.2),
    ]

    mock_reranker = MagicMock()
    mock_reranker.rerank.return_value = [(1, 0.9), (0, 0.1)]

    with patch.object(mcp_server, "_select_collection_names", fake_select), \
         patch.object(mcp_server, "_exact_chunk_name_results", fake_exact), \
         patch.object(mcp_server, "_doc_dedup_key", fake_dedup), \
         patch.object(mcp_server, "_load_symbols_vocab", fake_load_vocab), \
         patch.object(mcp_server, "get_reranker", return_value=mock_reranker), \
         patch.object(mcp_server, "HYBRID_SEARCH", False):
        results = mcp_server._sync_multi_search(
            "query", 2, "auto", "", "", {"col": fake_vs}
        )

    texts_passed = mock_reranker.rerank.call_args[0][1]
    assert texts_passed == ["aaa", "bbb"]
    assert results[0][0].page_content == "bbb"
    assert results[1][0].page_content == "aaa"


# ---------------------------------------------------------------------------
# RR-11: Exact chunk_name results preserved before reranked results
# ---------------------------------------------------------------------------

def test_rr11_exact_results_preserved(monkeypatch):
    import mcp_server

    exact_doc = _make_fake_doc("EXACT", {"_exact_match": "chunk_name"})
    regular_doc_a = _make_fake_doc("aaa")
    regular_doc_b = _make_fake_doc("bbb")

    def fake_select(cmap, st, domain):
        return ["col"]

    def fake_exact(query, targets, cmap, repo_filter, vocab):
        return [(exact_doc, 0.0, "code")]

    call_count = [0]

    def fake_dedup(doc):
        return doc.page_content

    def fake_load_vocab(db_path):
        return frozenset()

    fake_vs = MagicMock()
    fake_vs.similarity_search_with_score.return_value = [
        (regular_doc_a, 0.1),
        (regular_doc_b, 0.2),
    ]

    mock_reranker = MagicMock()
    mock_reranker.rerank.return_value = [(1, 0.9), (0, 0.1)]

    with patch.object(mcp_server, "_select_collection_names", fake_select), \
         patch.object(mcp_server, "_exact_chunk_name_results", fake_exact), \
         patch.object(mcp_server, "_doc_dedup_key", fake_dedup), \
         patch.object(mcp_server, "_load_symbols_vocab", fake_load_vocab), \
         patch.object(mcp_server, "get_reranker", return_value=mock_reranker), \
         patch.object(mcp_server, "HYBRID_SEARCH", False):
        results = mcp_server._sync_multi_search(
            "query", 3, "auto", "", "", {"col": fake_vs}
        )

    assert results[0][0].page_content == "EXACT"
    assert results[1][0].page_content == "bbb"


# ---------------------------------------------------------------------------
# RR-12: RAG_RERANKER_CANDIDATES controls pool size
# ---------------------------------------------------------------------------

def test_rr12_candidates_env_var(monkeypatch):
    import mcp_server

    docs = [_make_fake_doc(f"doc{i}") for i in range(20)]

    def fake_select(cmap, st, domain):
        return ["col"]

    def fake_exact(query, targets, cmap, repo_filter, vocab):
        return []

    def fake_dedup(doc):
        return doc.page_content

    def fake_load_vocab(db_path):
        return frozenset()

    fake_vs = MagicMock()
    fake_vs.similarity_search_with_score.return_value = [(d, float(i) * 0.05) for i, d in enumerate(docs)]

    captured_texts: list = []

    def capturing_rerank(query, texts, top_k=None):
        captured_texts.extend(texts)
        limit = top_k if top_k is not None else len(texts)
        return [(i, float(len(texts) - i)) for i in range(min(limit, len(texts)))]

    mock_reranker = MagicMock()
    mock_reranker.rerank.side_effect = capturing_rerank

    monkeypatch.setenv("RAG_RERANKER_CANDIDATES", "5")

    # Use k=10 so that merged[:k] can hold more than 5 items; the CANDIDATES=5 then limits
    # the pool passed to reranker.rerank, which is the assertion we care about.
    with patch.object(mcp_server, "_select_collection_names", fake_select), \
         patch.object(mcp_server, "_exact_chunk_name_results", fake_exact), \
         patch.object(mcp_server, "_doc_dedup_key", fake_dedup), \
         patch.object(mcp_server, "_load_symbols_vocab", fake_load_vocab), \
         patch.object(mcp_server, "get_reranker", return_value=mock_reranker), \
         patch.object(mcp_server, "HYBRID_SEARCH", False):
        mcp_server._sync_multi_search(
            "query", 10, "auto", "", "", {"col": fake_vs}
        )

    assert len(captured_texts) == 5


# ---------------------------------------------------------------------------
# RR-13: Default device is cuda:0
# ---------------------------------------------------------------------------

def test_rr13_default_device(monkeypatch):
    monkeypatch.setenv("RAG_RERANKER", "1")
    monkeypatch.delenv("RAG_RERANKER_DEVICE", raising=False)
    mod = _fresh_reranker_module()
    r = mod.get_reranker()
    assert r is not None
    assert r.device == "cuda:0"


# ---------------------------------------------------------------------------
# Pool limit (AC-3 over-fetch)
# ---------------------------------------------------------------------------

def test_rr14_rerank_pool_limit_off(monkeypatch):
    monkeypatch.delenv("RAG_RERANKER", raising=False)
    import reranker as mod

    assert mod.rerank_pool_limit(5) == 5


def test_rr15_rerank_pool_limit_overfetch(monkeypatch):
    monkeypatch.setenv("RAG_RERANKER", "1")
    monkeypatch.setenv("RAG_RERANKER_CANDIDATES", "30")
    import reranker as mod

    assert mod.rerank_pool_limit(5) == 30
    assert mod.rerank_pool_limit(50) == 50
