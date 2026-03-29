"""validate_embedding_dimension branches."""
from __future__ import annotations

from typing import Any, List
from unittest.mock import MagicMock

import pytest

import ingest as ing


class _ProbeEmb:
    def __init__(self, dim: int = 768):
        self._dim = dim

    def embed_query(self, text: str) -> List[float]:
        return [0.1] * self._dim

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [[0.2] * self._dim for _ in texts]


def test_validate_empty_collection_no_schema_ok():
    coll = MagicMock()
    coll.count.return_value = 0
    coll._model = None
    assert ing.validate_embedding_dimension(coll, _ProbeEmb(768), "c", "m") is None


def test_validate_empty_collection_schema_mismatch():
    coll = MagicMock()
    coll.count.return_value = 0
    m = MagicMock()
    m.dimension = 768
    coll._model = m
    err = ing.validate_embedding_dimension(coll, _ProbeEmb(1024), "c", "mxbai")
    assert err and "mismatch" in err.lower()


def test_validate_probe_failure_empty_schema():
    coll = MagicMock()
    coll.count.return_value = 0
    coll._model = MagicMock()
    coll._model.dimension = 768

    class Bad:
        def embed_query(self, t):
            raise RuntimeError("down")

    err = ing.validate_embedding_dimension(coll, Bad(), "c", "m")  # type: ignore[arg-type]
    assert err and "probe" in err.lower()


def test_validate_nonempty_mismatch():
    coll = MagicMock()
    coll.count.return_value = 5
    coll.get.return_value = {"embeddings": [[0.0] * 768]}
    err = ing.validate_embedding_dimension(coll, _ProbeEmb(1024), "c", "x")
    assert err and "768" in err and "1024" in err


def test_validate_nonempty_ok():
    coll = MagicMock()
    coll.count.return_value = 2
    coll.get.return_value = {"embeddings": [[0.0] * 768]}
    assert ing.validate_embedding_dimension(coll, _ProbeEmb(768), "c", "nomic") is None


def test_validate_count_exception_returns_none():
    coll = MagicMock()
    coll.count.side_effect = RuntimeError("no")
    assert ing.validate_embedding_dimension(coll, _ProbeEmb(), "c", "m") is None


def test_validate_no_embeddings_in_row():
    coll = MagicMock()
    coll.count.return_value = 1
    coll.get.return_value = {"embeddings": []}
    assert ing.validate_embedding_dimension(coll, _ProbeEmb(), "c", "m") is None
