"""FastAPI tests for Chunk Inspector file/chunk endpoints."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import pytest
from fastapi.testclient import TestClient

import gui_backend as gb


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(gb, "resolved_source_base", lambda: tmp_path)
    return TestClient(gb.app)


def test_api_file_raw_ok(client: TestClient, tmp_path: Path) -> None:
    (tmp_path / "a.c").write_text("int x;\n", encoding="utf-8")
    r = client.get("/api/file/raw", params={"path": "a.c"})
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("text/plain")
    assert r.text == "int x;\n"


def test_api_file_raw_404(client: TestClient) -> None:
    r = client.get("/api/file/raw", params={"path": "missing.c"})
    assert r.status_code == 404


def test_api_file_raw_requires_path(client: TestClient) -> None:
    r = client.get("/api/file/raw", params={"path": ""})
    assert r.status_code == 400


def test_api_file_raw_rejects_traversal(client: TestClient) -> None:
    r = client.get("/api/file/raw", params={"path": ".."})
    assert r.status_code == 400


def test_api_chunks_file_ok(client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "f.c").write_text("hello world", encoding="utf-8")

    expect_src = str((tmp_path / "f.c").resolve())

    class FakeColl:
        def get(self, where: Dict[str, Any], include: List[str]) -> Dict[str, Any]:
            assert where.get("source") == expect_src
            return {
                "ids": ["id1"],
                "documents": ["hello world"],
                "metadatas": [{"chunk_type": "device_load_function", "chunk_name": "foo"}],
            }

    async def fake_ensure(_dp: str) -> Any:
        return None, None, {"utest_code": FakeColl()}, "model"

    monkeypatch.setattr(gb, "ensure_chroma", fake_ensure)
    r = client.get("/api/chunks/file", params={"path": "f.c"})
    assert r.status_code == 200
    data = r.json()
    assert data["total_chunks"] == 1
    assert data["chunks"][0]["chunk_id"] == "id1"
    assert data["chunks"][0]["collection"] == "utest_code"
    assert data["chunks"][0]["metadata"]["chunk_type"] == "device_load_function"


def test_api_chunks_file_404_not_file(client: TestClient) -> None:
    r = client.get("/api/chunks/file", params={"path": "nope.c"})
    assert r.status_code == 404
