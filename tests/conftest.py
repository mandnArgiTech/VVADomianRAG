"""Shared fixtures: fake Ollama embeddings, quiet tqdm, temp dirs."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable, List, Optional
from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def _disable_tqdm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TQDM_DISABLE", "1")


@pytest.fixture(autouse=True)
def _ingest_embed_test_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep ingest tests offline and deterministic.

    - EMBED_ASYNC=0: async HTTP embed ignores patched OllamaEmbeddings (would hang or flake on real Ollama).
    - EMBED_HTTP=0: sync workers use LangChain embed_documents so patch_ollama_embeddings applies.
      (tests/test_ingest_embed_worker.py deletes EMBED_HTTP so worker tests still exercise the HTTP branch with mocks.)
    """
    monkeypatch.setenv("EMBED_ASYNC", "0")
    monkeypatch.setenv("EMBED_HTTP", "0")


@pytest.fixture
def tmp_vector_db(tmp_path: Path) -> Path:
    d = tmp_path / "vectordb"
    d.mkdir(parents=True, exist_ok=True)
    return d


class FakeOllamaEmbeddings:
    """Drop-in stub: fixed-dimension vectors, no network."""

    def __init__(self, model: str = "nomic-embed-text", dim: int = 768):
        self.model = model
        self._dim = dim

    def embed_query(self, text: str) -> List[float]:
        return [0.01 * (i % 7 + 1) for i in range(self._dim)]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [[0.02 * ((i + j) % 11 + 1) for i in range(self._dim)] for j, _ in enumerate(texts)]


@pytest.fixture
def fake_embedder() -> FakeOllamaEmbeddings:
    return FakeOllamaEmbeddings(dim=768)


@pytest.fixture
def patch_ollama_embeddings(monkeypatch: pytest.MonkeyPatch) -> Callable[..., FakeOllamaEmbeddings]:
    import ingest as ingest_mod

    def _factory(dim: int = 768) -> FakeOllamaEmbeddings:
        fe = FakeOllamaEmbeddings(dim=dim)

        def _ctor(*_a: Any, **_kw: Any) -> FakeOllamaEmbeddings:
            return fe

        monkeypatch.setattr(ingest_mod, "OllamaEmbeddings", _ctor)
        return fe

    return _factory


@pytest.fixture
def concept_registry_path(tmp_path: Path) -> Path:
    p = tmp_path / "concept_registry.json"
    p.write_text(
        '{"nms": {"snmp": "snmp,agent", "vlan": "vlan,bridge"}}',
        encoding="utf-8",
    )
    return p


@pytest.fixture(autouse=True)
def reset_shutdown_event():
    """Avoid cross-test pollution if ingest_run breaks mid-loop."""
    import ingest as ingest_mod

    ingest_mod.shutdown_event.clear()
    yield
    ingest_mod.shutdown_event.clear()
