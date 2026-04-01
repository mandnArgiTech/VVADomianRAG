"""embed_with_retry, embedding_worker, optional embed timeout."""
from __future__ import annotations

import queue
import threading
import time
from typing import List
from unittest.mock import MagicMock

import pytest

import ingest as ing


@pytest.fixture
def no_embed_sleep(monkeypatch):
    monkeypatch.setattr(ing.time, "sleep", lambda *_a, **_k: None)


def test_embed_with_retry_success(no_embed_sleep):
    emb = MagicMock()
    emb.embed_documents = MagicMock(return_value=[[0.1, 0.2], [0.3, 0.4]])
    out = ing.embed_with_retry(emb, ["a", "b"])  # type: ignore[arg-type]
    assert out is not None
    assert len(out) == 2


def test_embed_with_retry_split_batch(no_embed_sleep):
    """Fail on multi-doc batch, succeed on single-doc halves."""

    class Flaky:
        def embed_documents(self, texts: List[str]) -> List[List[float]]:
            if len(texts) > 1:
                raise RuntimeError("too many")
            return [[0.5, 0.5] for _ in texts]

    out = ing.embed_with_retry(Flaky(), ["a", "b", "c"])  # type: ignore[arg-type]
    assert out is not None
    assert len(out) == 3


def test_embed_with_retry_half_split_returns_none(no_embed_sleep):
    """Hit merge path where one half permanently fails (line a/b2 None)."""

    class PartialFail:
        def embed_documents(self, texts):
            if len(texts) == 2:
                raise RuntimeError("no batch of 2")
            return None

    assert ing.embed_with_retry(PartialFail(), ["x", "y"]) is None  # type: ignore[arg-type]


def test_embed_with_retry_total_failure(no_embed_sleep):
    class Bad:
        def embed_documents(self, texts: List[str]):
            raise RuntimeError("always")

    assert ing.embed_with_retry(Bad(), ["only"]) is None  # type: ignore[arg-type]


def test_embedding_worker_success(no_embed_sleep, monkeypatch):
    monkeypatch.setattr(
        ing,
        "embed_with_retry_http",
        lambda _model, texts: [[0.1], [0.2]] if len(texts) == 2 else None,
    )
    cq: queue.Queue = queue.Queue()
    rq: queue.Queue = queue.Queue()
    batch = [("id1", "t1", {"source": "s"}), ("id2", "t2", {"source": "s"})]
    cq.put(batch)
    cq.put(None)
    t = threading.Thread(target=ing.embedding_worker, args=("nomic-embed-text", 0, cq, rq))
    t.start()
    t.join(timeout=5)
    item = rq.get(timeout=2)
    assert item is not None
    ids, texts, metas, vecs = item
    assert len(ids) == 2


def test_embedding_worker_embed_none(no_embed_sleep, monkeypatch):
    monkeypatch.setattr(ing, "embed_with_retry_http", lambda *_a, **_k: None)
    cq: queue.Queue = queue.Queue()
    rq: queue.Queue = queue.Queue()
    cq.put([("i", "t", {"source": "s"})])
    cq.put(None)
    t = threading.Thread(target=ing.embedding_worker, args=("nomic-embed-text", 0, cq, rq))
    t.start()
    t.join(timeout=5)
    assert rq.get(timeout=2) is None


def test_embedding_worker_exception(no_embed_sleep, monkeypatch):
    def boom(_m, _t):
        raise RuntimeError("boom")

    monkeypatch.setattr(ing, "embed_with_retry_http", boom)
    cq: queue.Queue = queue.Queue()
    rq: queue.Queue = queue.Queue()
    cq.put([("i", "t", {"source": "s"})])
    cq.put(None)
    t = threading.Thread(target=ing.embedding_worker, args=("nomic-embed-text", 0, cq, rq))
    t.start()
    t.join(timeout=5)
    assert rq.get(timeout=2) is None


def test_embedding_worker_langchain_path(no_embed_sleep, monkeypatch):
    monkeypatch.setenv("EMBED_HTTP", "0")
    mock_emb = MagicMock()
    mock_emb.embed_documents = MagicMock(return_value=[[0.9]])
    monkeypatch.setattr(ing, "OllamaEmbeddings", lambda model: mock_emb)
    cq: queue.Queue = queue.Queue()
    rq: queue.Queue = queue.Queue()
    cq.put([("i", "t", {"source": "s"})])
    cq.put(None)
    t = threading.Thread(target=ing.embedding_worker, args=("nomic-embed-text", 0, cq, rq))
    t.start()
    t.join(timeout=5)
    item = rq.get(timeout=2)
    assert item is not None
    mock_emb.embed_documents.assert_called()


def test_embed_documents_no_timeout():
    emb = MagicMock()
    emb.embed_documents = MagicMock(return_value=[[1.0]])
    out = ing._embed_documents_with_optional_timeout(emb, ["x"], None)  # type: ignore[arg-type]
    assert out == [[1.0]]


def test_embed_documents_timeout_raises():
    emb = MagicMock()

    def slow(*_a, **_k):
        time.sleep(30.0)
        return [[1.0]]

    emb.embed_documents = slow
    with pytest.raises(RuntimeError, match="timed out"):
        ing._embed_documents_with_optional_timeout(emb, ["x"], 0.05)  # type: ignore[arg-type]


def test_embed_documents_zero_timeout_uses_direct():
    emb = MagicMock()
    emb.embed_documents = MagicMock(return_value=[[2.0]])
    out = ing._embed_documents_with_optional_timeout(emb, ["z"], 0)  # type: ignore[arg-type]
    assert out == [[2.0]]
