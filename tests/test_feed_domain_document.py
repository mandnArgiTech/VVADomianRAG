"""feed_domain_document (MCP path)."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

import ingest as ing


def test_feed_domain_markdown(tmp_path, monkeypatch, fake_embedder):
    monkeypatch.setattr(ing, "OllamaEmbeddings", lambda **kw: fake_embedder)
    f = tmp_path / "d.md"
    f.write_text("# Doc\n\n## S\n\nsnmp agent\n", encoding="utf-8")
    db = tmp_path / "db"
    reg = tmp_path / "cr.json"
    reg.write_text("{}", encoding="utf-8")
    out = ing.feed_domain_document(
        str(f),
        "utest",
        str(db),
        "nomic-embed-text",
        concept_registry_path=str(reg),
        source_type="domain_doc",
    )
    assert out["chunk_count"] >= 1
    assert "collection" in out


def test_feed_domain_rfc_named_file(tmp_path, monkeypatch, fake_embedder):
    monkeypatch.setattr(ing, "OllamaEmbeddings", lambda **kw: fake_embedder)
    f = tmp_path / "rfc791.txt"
    f.write_text(
        "Network Working Group\n\nRFC 791\n\n1. INTRO\n\nInternet Protocol.\n",
        encoding="utf-8",
    )
    db = tmp_path / "db"
    reg = tmp_path / "cr.json"
    reg.write_text("{}", encoding="utf-8")
    out = ing.feed_domain_document(
        str(f),
        "utest",
        str(db),
        "nomic-embed-text",
        concept_registry_path=str(reg),
        source_type="auto",
    )
    assert out["chunk_count"] >= 1


def test_feed_domain_no_lock(tmp_path, monkeypatch, fake_embedder):
    monkeypatch.setattr(ing, "OllamaEmbeddings", lambda **kw: fake_embedder)
    f = tmp_path / "d.md"
    f.write_text("# X\n\nY\n", encoding="utf-8")
    db = tmp_path / "db"
    reg = tmp_path / "cr.json"
    reg.write_text("{}", encoding="utf-8")
    out = ing.feed_domain_document(
        str(f),
        "utest",
        str(db),
        "nomic-embed-text",
        concept_registry_path=str(reg),
        use_embed_lock=False,
    )
    assert out["chunk_count"] >= 1


def test_feed_domain_invalid_source_type_normalized(tmp_path, monkeypatch, fake_embedder):
    monkeypatch.setattr(ing, "OllamaEmbeddings", lambda **kw: fake_embedder)
    f = tmp_path / "d.md"
    f.write_text("# X\n\nY\n", encoding="utf-8")
    db = tmp_path / "db"
    reg = tmp_path / "cr.json"
    reg.write_text("{}", encoding="utf-8")
    out = ing.feed_domain_document(
        str(f),
        "utest",
        str(db),
        "nomic-embed-text",
        concept_registry_path=str(reg),
        source_type="bogus",
    )
    assert out["chunk_count"] >= 1


def test_feed_domain_dim_mismatch_raises(tmp_path, monkeypatch):
    f = tmp_path / "d.md"
    f.write_text("# X\n", encoding="utf-8")
    reg = tmp_path / "cr.json"
    reg.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        ing,
        "validate_embedding_dimension",
        lambda *a, **k: "Embedding dimension mismatch for collection",
    )
    with pytest.raises(RuntimeError, match="mismatch"):
        ing.feed_domain_document(
            str(f),
            "utest",
            str(tmp_path / "db"),
            "mxbai-embed-large",
            concept_registry_path=str(reg),
        )


def test_feed_domain_embed_timeout(tmp_path, monkeypatch):
    f = tmp_path / "d.md"
    f.write_text("# X\n\n" + "word " * 50 + "\n", encoding="utf-8")
    db = tmp_path / "db"
    reg = tmp_path / "cr.json"
    reg.write_text("{}", encoding="utf-8")

    class Slow:
        def embed_query(self, t):
            return [0.1] * 768

        def embed_documents(self, texts):
            import time

            time.sleep(2.0)
            return [[0.2] * 768 for _ in texts]

    monkeypatch.setattr(ing, "OllamaEmbeddings", lambda **kw: Slow())
    with pytest.raises(RuntimeError, match="timed out"):
        ing.feed_domain_document(
            str(f),
            "utest",
            str(db),
            "nomic-embed-text",
            concept_registry_path=str(reg),
            embed_batch_timeout=0.05,
        )


def test_feed_domain_lock_timeout(tmp_path, monkeypatch, fake_embedder):
    f = tmp_path / "d.md"
    f.write_text("# X\n\nY\n", encoding="utf-8")
    db = tmp_path / "db"
    reg = tmp_path / "cr.json"
    reg.write_text("{}", encoding="utf-8")
    mock_lock = MagicMock()
    mock_lock.acquire.return_value = False
    monkeypatch.setattr(ing, "_embed_lock", mock_lock)
    monkeypatch.setattr(ing, "OllamaEmbeddings", lambda **kw: fake_embedder)
    with pytest.raises(RuntimeError, match="embedding lock"):
        ing.feed_domain_document(
            str(f),
            "utest",
            str(db),
            "nomic-embed-text",
            concept_registry_path=str(reg),
        )
