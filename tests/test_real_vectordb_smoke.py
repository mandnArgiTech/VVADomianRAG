"""
Smoke tests against the real Chroma persist dir (optional).

Default CI / local runs: skipped (set REAL_VECTORDB_TESTS=1 to enable).

Examples (use the same Python env as DomainRAG, e.g. Studio-Portable-RAG/Python/bin/python3):

  PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 REAL_VECTORDB_TESTS=1 \\
    Studio-Portable-RAG/Python/bin/python3 -m pytest tests/test_real_vectordb_smoke.py -v --no-cov

  Optional: DB_PATH=/path/to/VectorDB (defaults to <repo>/Studio-Portable-RAG/VectorDB).

If pytest fails with "Plugin already registered ... timeout", ROS/colcon entry points are
colliding with pytest-timeout; keep PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 as above.
"""
from __future__ import annotations

import os
import urllib.request
from pathlib import Path

import pytest

REAL = os.environ.get("REAL_VECTORDB_TESTS", "").strip().lower() in ("1", "yes", "true")

pytestmark = pytest.mark.skipif(
    not REAL,
    reason="Set REAL_VECTORDB_TESTS=1 to run real VectorDB smoke tests",
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _resolve_db_path() -> Path:
    env = os.environ.get("DB_PATH", "").strip()
    if env:
        return Path(env).resolve()
    return (_repo_root() / "Studio-Portable-RAG" / "VectorDB").resolve()


@pytest.fixture(scope="module")
def real_db_path() -> Path:
    p = _resolve_db_path()
    sqlite = p / "chroma.sqlite3"
    if not p.is_dir() or not sqlite.is_file():
        pytest.skip(f"Real VectorDB missing (need directory + chroma.sqlite3): {p}")
    return p


def _ollama_up() -> bool:
    try:
        urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=3)
        return True
    except Exception:
        return False


def test_real_db_lists_general_code_collection(real_db_path: Path) -> None:
    import chromadb

    client = chromadb.PersistentClient(path=str(real_db_path))
    names = {c.name for c in client.list_collections()}
    assert "general_code" in names, f"expected general_code in {sorted(names)}"


def test_real_db_general_code_has_chunks(real_db_path: Path) -> None:
    import chromadb

    client = chromadb.PersistentClient(path=str(real_db_path))
    coll = client.get_collection("general_code")
    n = coll.count()
    assert n > 100, f"general_code unexpectedly small: {n}"


def test_real_db_semantic_search_general_code(real_db_path: Path) -> None:
    """Same routing as MCP search_knowledge(code, domain=general_code)."""
    if not _ollama_up():
        pytest.skip("Ollama not reachable at http://127.0.0.1:11434/api/tags")

    import chromadb
    from langchain_chroma import Chroma
    from langchain_ollama import OllamaEmbeddings

    import query as query_mod

    cfg = real_db_path / "ingestion_config.json"
    model = "nomic-embed-text"
    if cfg.is_file():
        import json

        try:
            model = json.loads(cfg.read_text(encoding="utf-8")).get("embedding_model") or model
        except Exception:
            pass

    client = chromadb.PersistentClient(path=str(real_db_path))
    embedder = OllamaEmbeddings(model=model)
    cmap: dict[str, Chroma] = {}
    for info in client.list_collections():
        cmap[info.name] = Chroma(
            collection_name=info.name,
            persist_directory=str(real_db_path),
            embedding_function=embedder,
        )

    hits = query_mod._sync_multi_search(
        "function definition error handling",
        k=4,
        search_type="code",
        domain="general_code",
        repo_filter="",
        cmap=cmap,
    )
    assert len(hits) >= 1
    texts = [h.content for h in hits]
    assert any(len(t.strip()) > 20 for t in texts)


def test_real_db_search_codebase_equivalent_all_code_collections(real_db_path: Path) -> None:
    """MCP search_codebase → search_knowledge(search_type=code, domain='')."""
    if not _ollama_up():
        pytest.skip("Ollama not reachable at http://127.0.0.1:11434/api/tags")

    import chromadb
    from langchain_chroma import Chroma
    from langchain_ollama import OllamaEmbeddings

    import query as query_mod

    cfg = real_db_path / "ingestion_config.json"
    model = "nomic-embed-text"
    if cfg.is_file():
        import json

        try:
            model = json.loads(cfg.read_text(encoding="utf-8")).get("embedding_model") or model
        except Exception:
            pass

    client = chromadb.PersistentClient(path=str(real_db_path))
    embedder = OllamaEmbeddings(model=model)
    cmap: dict[str, Chroma] = {}
    for info in client.list_collections():
        cmap[info.name] = Chroma(
            collection_name=info.name,
            persist_directory=str(real_db_path),
            embedding_function=embedder,
        )

    hits = query_mod._sync_multi_search(
        "async def main",
        k=3,
        search_type="code",
        domain="",
        repo_filter="",
        cmap=cmap,
    )
    assert len(hits) >= 1
