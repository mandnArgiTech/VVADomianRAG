"""Shared fixtures: fake Ollama embeddings, quiet tqdm, temp dirs."""
from __future__ import annotations

import json
import os
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, List, Optional
from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def _disable_tqdm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TQDM_DISABLE", "1")


class _FakeOllamaHTTPHandler(BaseHTTPRequestHandler):
    """Minimal Ollama /api/embed + /api/tags stub so the HTTP/async embedding
    paths work hermetically when no real Ollama is running on :11434."""

    def _send_json(self, obj: Any) -> None:
        body = json.dumps(obj).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # /api/tags, health checks
        self._send_json({"models": []})

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        payload = json.loads(self.rfile.read(length) or b"{}")
        inp = payload.get("input", [])
        if isinstance(inp, str):
            inp = [inp]
        dim = 768
        vecs = [[0.02 * ((i + j) % 11 + 1) for i in range(dim)] for j, _ in enumerate(inp)]
        self._send_json({"embeddings": vecs})

    def log_message(self, *_a: Any) -> None:  # silence request logging
        return


@pytest.fixture(scope="session", autouse=True)
def _fake_ollama_server():
    """Serve a fake Ollama on 127.0.0.1:11434 unless something already listens
    there (a real Ollama). Makes EMBED_HTTP/EMBED_ASYNC ingest paths hermetic."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.2)
        in_use = probe.connect_ex(("127.0.0.1", 11434)) == 0
    if in_use:
        yield None
        return
    try:
        server = ThreadingHTTPServer(("127.0.0.1", 11434), _FakeOllamaHTTPHandler)
    except OSError:  # port raced/unavailable; fall back to real behavior
        yield None
        return
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    yield server
    server.shutdown()


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
