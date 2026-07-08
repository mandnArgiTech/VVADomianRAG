"""ingest_run and main() integration with temp Chroma + fake embeddings."""
from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import chromadb
import pytest

import ingest as ing


def _args(parser, *cli):
    return parser.parse_args(list(cli))


def test_ingest_status_mode(tmp_vector_db, capsys):
    p = ing.build_arg_parser()
    args = _args(
        p,
        "--mode",
        "status",
        "--db-path",
        str(tmp_vector_db),
    )
    assert ing.ingest_run(args) == 0
    assert "DOMAIN RAG" in capsys.readouterr().out


def test_ingest_domain_dry_run(tmp_path, monkeypatch, patch_ollama_embeddings, concept_registry_path):
    monkeypatch.setenv("EMBEDDING_MODEL", "nomic-embed-text")
    patch_ollama_embeddings(dim=768)
    src = tmp_path / "docs"
    src.mkdir()
    (src / "note.md").write_text("# Title\n\n## Section\n\nHello snmp agent.\n", encoding="utf-8")
    db = tmp_path / "vdb"
    p = ing.build_arg_parser()
    args = _args(
        p,
        "--mode",
        "domain",
        "--domain",
        "utest",
        "--source",
        str(src),
        "--db-path",
        str(db),
        "--concept-registry",
        str(concept_registry_path),
        "--dry-run",
    )
    assert ing.ingest_run(args) == 0


def test_ingest_domain_full_ingest(tmp_path, monkeypatch, patch_ollama_embeddings, concept_registry_path):
    monkeypatch.setenv("EMBEDDING_MODEL", "nomic-embed-text")
    monkeypatch.setenv("EMBED_WORKERS", "1")
    patch_ollama_embeddings(dim=768)
    src = tmp_path / "docs"
    src.mkdir()
    (src / "note.md").write_text("# T\n\n## S\n\nBody snmp\n" * 5, encoding="utf-8")
    db = tmp_path / "vdb"
    p = ing.build_arg_parser()
    args = _args(
        p,
        "--mode",
        "domain",
        "--domain",
        "utest",
        "--source",
        str(src),
        "--db-path",
        str(db),
        "--concept-registry",
        str(concept_registry_path),
        "--force",
    )
    assert ing.ingest_run(args) == 0
    client = chromadb.PersistentClient(path=str(db))
    cols = [c.name for c in client.list_collections()]
    assert any("utest" in n for n in cols)


def test_ingest_partial_embed_failure_keeps_file_for_retry(
    tmp_path, monkeypatch, patch_ollama_embeddings, concept_registry_path
):
    """A file whose chunks fail embedding must NOT be checkpointed as done,
    while sibling files that embedded fine are recorded and written."""
    monkeypatch.setenv("EMBEDDING_MODEL", "nomic-embed-text")
    monkeypatch.setenv("EMBED_WORKERS", "1")
    monkeypatch.setenv("EMBED_ASYNC", "0")
    monkeypatch.setenv("EMBED_HTTP", "0")
    patch_ollama_embeddings(dim=768)

    def fake_retry(_embedder, batch):
        return [None if "FAILME" in t else [0.01] * 768 for t in batch]

    monkeypatch.setattr(ing, "embed_with_retry", fake_retry)

    src = tmp_path / "docs"
    src.mkdir()
    (src / "ok.md").write_text("# T\n\n## S\n\nGood body snmp\n", encoding="utf-8")
    (src / "bad.md").write_text("# T\n\n## S\n\nFAILME body\n", encoding="utf-8")
    db = tmp_path / "vdb"
    p = ing.build_arg_parser()
    args = _args(
        p,
        "--mode",
        "domain",
        "--domain",
        "utest",
        "--source",
        str(src),
        "--db-path",
        str(db),
        "--concept-registry",
        str(concept_registry_path),
        "--force",
    )
    assert ing.ingest_run(args) == 0

    ck = ing.load_checkpoint(db)
    hashes = {}
    for key, val in ck.items():
        if key.endswith("::checkpoint"):
            hashes.update(json.loads(val))
    recorded = "\n".join(hashes.keys())
    assert "ok.md" in recorded
    assert "bad.md" not in recorded  # failed file re-ingests next run

    client = chromadb.PersistentClient(path=str(db))
    col = next(c for c in client.list_collections() if "utest" in c.name)
    got = client.get_collection(col.name).get(include=["metadatas"])
    sources = {m.get("source", "") for m in got["metadatas"]}
    assert any(s.endswith("ok.md") for s in sources)
    assert not any(s.endswith("bad.md") for s in sources)


def test_ingest_all_chunks_fail_embedding_batch_skipped(
    tmp_path, monkeypatch, patch_ollama_embeddings, concept_registry_path
):
    """Whole batch failing embedding: nothing upserted, file not checkpointed."""
    monkeypatch.setenv("EMBEDDING_MODEL", "nomic-embed-text")
    monkeypatch.setenv("EMBED_WORKERS", "1")
    monkeypatch.setenv("EMBED_ASYNC", "0")
    monkeypatch.setenv("EMBED_HTTP", "0")
    patch_ollama_embeddings(dim=768)
    monkeypatch.setattr(ing, "embed_with_retry", lambda _e, batch: [None] * len(batch))

    src = tmp_path / "docs"
    src.mkdir()
    (src / "bad.md").write_text("# T\n\n## S\n\nDoomed body\n", encoding="utf-8")
    db = tmp_path / "vdb"
    p = ing.build_arg_parser()
    args = _args(
        p, "--mode", "domain", "--domain", "utest", "--source", str(src),
        "--db-path", str(db), "--concept-registry", str(concept_registry_path), "--force",
    )
    assert ing.ingest_run(args) == 0
    ck = ing.load_checkpoint(db)
    joined = "".join(v for k, v in ck.items() if k.endswith("::checkpoint"))
    assert "bad.md" not in joined


def test_ingest_interrupted_run_keeps_previous_checkpoint(
    tmp_path, monkeypatch, patch_ollama_embeddings, concept_registry_path
):
    """shutdown_event set => checkpoint untouched (files re-ingest next run)."""
    monkeypatch.setenv("EMBEDDING_MODEL", "nomic-embed-text")
    monkeypatch.setenv("EMBED_WORKERS", "1")
    monkeypatch.setenv("EMBED_ASYNC", "0")
    monkeypatch.setenv("EMBED_HTTP", "0")
    patch_ollama_embeddings(dim=768)

    src = tmp_path / "docs"
    src.mkdir()
    (src / "note.md").write_text("# T\n\n## S\n\nBody snmp\n", encoding="utf-8")
    db = tmp_path / "vdb"
    db.mkdir()
    ing.save_checkpoint(db, {"sentinel::checkpoint": "{}"})
    ing.shutdown_event.set()
    try:
        p = ing.build_arg_parser()
        args = _args(
            p, "--mode", "domain", "--domain", "utest", "--source", str(src),
            "--db-path", str(db), "--concept-registry", str(concept_registry_path), "--force",
        )
        assert ing.ingest_run(args) == 0
    finally:
        ing.shutdown_event.clear()
    ck = ing.load_checkpoint(db)
    assert "sentinel::checkpoint" in ck  # previous state preserved
    assert not any("utest" in k for k in ck)  # nothing new recorded


def test_ingest_rfc_dry_run(tmp_path, monkeypatch, patch_ollama_embeddings, concept_registry_path):
    monkeypatch.setenv("EMBEDDING_MODEL", "nomic-embed-text")
    patch_ollama_embeddings(dim=768)
    src = tmp_path / "r"
    src.mkdir()
    (src / "rfc2549.txt").write_text(
        "Network Working Group\n\nRequest for Comments: 2549\n\n1. INTRO\n\nIP over Avian Carriers.\n",
        encoding="utf-8",
    )
    db = tmp_path / "vdb"
    p = ing.build_arg_parser()
    args = _args(
        p,
        "--mode",
        "rfc",
        "--source",
        str(src),
        "--db-path",
        str(db),
        "--concept-registry",
        str(concept_registry_path),
        "--dry-run",
    )
    assert ing.ingest_run(args) == 0


def test_ingest_code_python(tmp_path, monkeypatch, patch_ollama_embeddings, concept_registry_path):
    monkeypatch.setenv("EMBEDDING_MODEL", "nomic-embed-text")
    monkeypatch.setenv("EMBED_WORKERS", "1")
    patch_ollama_embeddings(dim=768)
    src = tmp_path / "code"
    src.mkdir()
    (src / "m.py").write_text("def f():\n    return 42\n", encoding="utf-8")
    db = tmp_path / "vdb"
    p = ing.build_arg_parser()
    args = _args(
        p,
        "--mode",
        "code",
        "--domain",
        "utest",
        "--source",
        str(src),
        "--db-path",
        str(db),
        "--concept-registry",
        str(concept_registry_path),
        "--force",
    )
    assert ing.ingest_run(args) == 0


def test_ingest_customer_json(tmp_path, monkeypatch, patch_ollama_embeddings, concept_registry_path):
    monkeypatch.setenv("EMBEDDING_MODEL", "nomic-embed-text")
    monkeypatch.setenv("EMBED_WORKERS", "1")
    patch_ollama_embeddings(dim=768)
    src = tmp_path / "tix"
    src.mkdir()
    ticket = {"ticket_id": "1", "subject": "Subj", "description": "Desc body"}
    (src / "t1.json").write_text(json.dumps(ticket), encoding="utf-8")
    db = tmp_path / "vdb"
    p = ing.build_arg_parser()
    args = _args(
        p,
        "--mode",
        "customer",
        "--domain",
        "utest",
        "--source",
        str(src),
        "--db-path",
        str(db),
        "--concept-registry",
        str(concept_registry_path),
        "--force",
    )
    assert ing.ingest_run(args) == 0


def test_ingest_community_frontmatter(tmp_path, monkeypatch, patch_ollama_embeddings, concept_registry_path):
    monkeypatch.setenv("EMBEDDING_MODEL", "nomic-embed-text")
    monkeypatch.setenv("EMBED_WORKERS", "1")
    patch_ollama_embeddings(dim=768)
    src = tmp_path / "com"
    src.mkdir()
    body = "---\nsource_platform: slack\n---\nDiscussion thread text.\n"
    (src / "th.md").write_text(body, encoding="utf-8")
    db = tmp_path / "vdb"
    p = ing.build_arg_parser()
    args = _args(
        p,
        "--mode",
        "community",
        "--domain",
        "utest",
        "--source",
        str(src),
        "--db-path",
        str(db),
        "--concept-registry",
        str(concept_registry_path),
        "--force",
    )
    assert ing.ingest_run(args) == 0


def test_ingest_release_notes(tmp_path, monkeypatch, patch_ollama_embeddings, concept_registry_path):
    monkeypatch.setenv("EMBEDDING_MODEL", "nomic-embed-text")
    monkeypatch.setenv("EMBED_WORKERS", "1")
    patch_ollama_embeddings(dim=768)
    src = tmp_path / "rel"
    src.mkdir()
    (src / "CHANGELOG.md").write_text("# 1.0.0\n\n## Bug Fixes\n\nFixed snmp issue.\n", encoding="utf-8")
    db = tmp_path / "vdb"
    p = ing.build_arg_parser()
    args = _args(
        p,
        "--mode",
        "release-notes",
        "--domain",
        "utest",
        "--source",
        str(src),
        "--db-path",
        str(db),
        "--concept-registry",
        str(concept_registry_path),
        "--force",
    )
    assert ing.ingest_run(args) == 0


def test_ingest_mib(tmp_path, monkeypatch, patch_ollama_embeddings, concept_registry_path):
    monkeypatch.setenv("EMBEDDING_MODEL", "nomic-embed-text")
    monkeypatch.setenv("EMBED_WORKERS", "1")
    patch_ollama_embeddings(dim=768)
    src = tmp_path / "mibs"
    src.mkdir()
    mib = """
TEST-MIB DEFINITIONS ::= BEGIN
o OBJECT-TYPE
    SYNTAX INTEGER
    MAX-ACCESS read-only
    STATUS current
    DESCRIPTION "t"
    ::= { 1 3 }
END
"""
    (src / "T.mib").write_text(mib, encoding="utf-8")
    db = tmp_path / "vdb"
    p = ing.build_arg_parser()
    args = _args(
        p,
        "--mode",
        "mib",
        "--source",
        str(src),
        "--db-path",
        str(db),
        "--concept-registry",
        str(concept_registry_path),
        "--force",
    )
    assert ing.ingest_run(args) == 0


def test_ingest_theory_md(tmp_path, monkeypatch, patch_ollama_embeddings, concept_registry_path):
    monkeypatch.setenv("EMBEDDING_MODEL", "nomic-embed-text")
    monkeypatch.setenv("EMBED_WORKERS", "1")
    patch_ollama_embeddings(dim=768)
    src = tmp_path / "th"
    src.mkdir()
    (src / "t.md").write_text("# Theory\n\n## Note\n\nText.\n", encoding="utf-8")
    db = tmp_path / "vdb"
    p = ing.build_arg_parser()
    args = _args(
        p,
        "--mode",
        "theory",
        "--domain",
        "utest",
        "--source",
        str(src),
        "--db-path",
        str(db),
        "--concept-registry",
        str(concept_registry_path),
        "--force",
    )
    assert ing.ingest_run(args) == 0


def test_ingest_wiki_html_file(tmp_path, monkeypatch, patch_ollama_embeddings, concept_registry_path):
    monkeypatch.setenv("EMBEDDING_MODEL", "nomic-embed-text")
    monkeypatch.setenv("EMBED_WORKERS", "1")
    patch_ollama_embeddings(dim=768)
    src = tmp_path / "w"
    src.mkdir()
    html = "<html><body><p>" + ("word " * 100) + "</p></body></html>"
    (src / "p.html").write_text(html, encoding="utf-8")
    db = tmp_path / "vdb"
    p = ing.build_arg_parser()
    args = _args(
        p,
        "--mode",
        "wiki",
        "--domain",
        "utest",
        "--source",
        str(src),
        "--db-path",
        str(db),
        "--concept-registry",
        str(concept_registry_path),
        "--force",
    )
    assert ing.ingest_run(args) == 0


def test_ingest_rally_json_file(tmp_path, monkeypatch, patch_ollama_embeddings, concept_registry_path):
    monkeypatch.setenv("EMBEDDING_MODEL", "nomic-embed-text")
    monkeypatch.setenv("EMBED_WORKERS", "1")
    patch_ollama_embeddings(dim=768)
    src = tmp_path / "ral"
    src.mkdir()
    obj = {
        "FormattedID": "DE9",
        "Name": "Bug",
        "Description": "x" * 300,
        "Severity": "2",
        "State": "Open",
    }
    (src / "one.json").write_text(json.dumps(obj), encoding="utf-8")
    db = tmp_path / "vdb"
    p = ing.build_arg_parser()
    args = _args(
        p,
        "--mode",
        "rally",
        "--domain",
        "utest",
        "--source",
        str(src / "one.json"),
        "--db-path",
        str(db),
        "--concept-registry",
        str(concept_registry_path),
        "--force",
    )
    assert ing.ingest_run(args) == 0


def test_ingest_checkpoint_skip_without_force(tmp_path, monkeypatch, patch_ollama_embeddings, concept_registry_path):
    monkeypatch.setenv("EMBEDDING_MODEL", "nomic-embed-text")
    monkeypatch.setenv("EMBED_WORKERS", "1")
    patch_ollama_embeddings(dim=768)
    src = tmp_path / "docs"
    src.mkdir()
    f = src / "same.md"
    f.write_text("# X\n\nY\n", encoding="utf-8")
    db = tmp_path / "vdb"
    p = ing.build_arg_parser()
    args1 = _args(
        p,
        "--mode",
        "domain",
        "--domain",
        "utest",
        "--source",
        str(src),
        "--db-path",
        str(db),
        "--concept-registry",
        str(concept_registry_path),
        "--force",
    )
    assert ing.ingest_run(args1) == 0
    args2 = _args(
        p,
        "--mode",
        "domain",
        "--domain",
        "utest",
        "--source",
        str(src),
        "--db-path",
        str(db),
        "--concept-registry",
        str(concept_registry_path),
    )
    assert ing.ingest_run(args2) == 0


def test_ingest_dimension_recreate_path(monkeypatch, tmp_path, patch_ollama_embeddings, concept_registry_path):
    """Exercise validate failure + delete_collection + re-validate success (mocked)."""
    monkeypatch.setenv("EMBEDDING_MODEL", "nomic-embed-text")
    monkeypatch.setenv("EMBED_WORKERS", "1")
    patch_ollama_embeddings(dim=768)
    src = tmp_path / "docs"
    src.mkdir()
    (src / "n.md").write_text("# A\n\nB\n", encoding="utf-8")
    db = tmp_path / "vdb"
    p = ing.build_arg_parser()
    base_args = [
        "--mode",
        "domain",
        "--domain",
        "utest",
        "--source",
        str(src),
        "--db-path",
        str(db),
        "--concept-registry",
        str(concept_registry_path),
        "--force",
    ]
    calls: list = []

    def fake_validate(coll, embedder, name, model):
        calls.append(1)
        if len(calls) == 1:
            return "Embedding dimension mismatch"
        return None

    monkeypatch.setattr(ing, "validate_embedding_dimension", fake_validate)
    deleted = {"n": 0}
    real_pc = chromadb.PersistentClient

    def persistent_client_shim(path=None, **kwargs):
        base = real_pc(path=str(path), **kwargs)

        class Shim:
            def __getattr__(self, name):
                return getattr(base, name)

            def delete_collection(self, name):
                deleted["n"] += 1
                return base.delete_collection(name=name)

        return Shim()

    monkeypatch.setattr(chromadb, "PersistentClient", persistent_client_shim)
    args = _args(p, *base_args, "--recreate-collection")
    assert ing.ingest_run(args) == 0
    assert deleted["n"] >= 1


def test_ingest_clean_stale(tmp_path, monkeypatch, patch_ollama_embeddings, concept_registry_path):
    monkeypatch.setenv("EMBEDDING_MODEL", "nomic-embed-text")
    monkeypatch.setenv("EMBED_WORKERS", "1")
    patch_ollama_embeddings(dim=768)
    src = tmp_path / "docs"
    src.mkdir()
    f = src / "keep.md"
    f.write_text("# K\n\nText\n", encoding="utf-8")
    db = tmp_path / "vdb"
    p = ing.build_arg_parser()
    args1 = _args(
        p,
        "--mode",
        "domain",
        "--domain",
        "utest",
        "--source",
        str(src),
        "--db-path",
        str(db),
        "--concept-registry",
        str(concept_registry_path),
        "--force",
    )
    assert ing.ingest_run(args1) == 0
    ghost = str(tmp_path / "missing.md")
    ck = ing.load_checkpoint(db)
    key = f"{ing.resolve_collection('domain', 'utest', None)}::checkpoint"
    hashes = json.loads(ck.get(key, "{}"))
    hashes[ghost] = "deadbeef"
    ck[key] = json.dumps(hashes)
    ing.save_checkpoint(db, ck)
    args2 = _args(
        p,
        "--mode",
        "domain",
        "--domain",
        "utest",
        "--source",
        str(src),
        "--db-path",
        str(db),
        "--concept-registry",
        str(concept_registry_path),
        "--clean-stale",
        "--force",
    )
    assert ing.ingest_run(args2) == 0


@patch("ingest.fetch_rally_artifacts")
def test_ingest_rally_virtual_api(mock_fetch, tmp_path, monkeypatch, patch_ollama_embeddings, concept_registry_path):
    monkeypatch.setenv("EMBEDDING_MODEL", "nomic-embed-text")
    monkeypatch.setenv("EMBED_WORKERS", "1")
    patch_ollama_embeddings(dim=768)
    mock_fetch.return_value = [
        {
            "FormattedID": "DE1",
            "Name": "T",
            "Description": "d" * 300,
            "Severity": "2",
            "State": "Open",
            "Tags": "",
        }
    ]
    db = tmp_path / "vdb"
    p = ing.build_arg_parser()
    args = _args(
        p,
        "--mode",
        "rally",
        "--domain",
        "utest",
        "--rally-project",
        "P",
        "--db-path",
        str(db),
        "--concept-registry",
        str(concept_registry_path),
        "--force",
    )
    monkeypatch.delenv("SOURCE_FOLDER", raising=False)
    assert ing.ingest_run(args) == 0


@patch("ingest.fetch_confluence_pages")
def test_ingest_wiki_virtual_api(mock_pages, tmp_path, monkeypatch, patch_ollama_embeddings, concept_registry_path):
    monkeypatch.setenv("EMBEDDING_MODEL", "nomic-embed-text")
    monkeypatch.setenv("EMBED_WORKERS", "1")
    patch_ollama_embeddings(dim=768)
    mock_pages.return_value = [
        {
            "title": "Long page",
            "space": "S",
            "labels": "",
            "author": "",
            "last_modified": "",
            "parent_page": "",
            "page_url": "http://x/p",
            "body": "B" * 250,
        }
    ]
    db = tmp_path / "vdb"
    p = ing.build_arg_parser()
    args = _args(
        p,
        "--mode",
        "wiki",
        "--domain",
        "utest",
        "--confluence-space",
        "SPC",
        "--db-path",
        str(db),
        "--concept-registry",
        str(concept_registry_path),
        "--force",
    )
    monkeypatch.delenv("SOURCE_FOLDER", raising=False)
    assert ing.ingest_run(args) == 0


def test_ingest_rally_no_requests_errors(tmp_path, monkeypatch):
    monkeypatch.setattr(ing, "requests", None)
    db = tmp_path / "vdb"
    p = ing.build_arg_parser()
    args = _args(
        p,
        "--mode",
        "rally",
        "--rally-project",
        "P",
        "--db-path",
        str(db),
        "--concept-registry",
        str(tmp_path / "cr.json"),
    )
    (tmp_path / "cr.json").write_text("{}", encoding="utf-8")
    monkeypatch.delenv("SOURCE_FOLDER", raising=False)
    assert ing.ingest_run(args) == 2


def test_ingest_no_source_errors(tmp_path, monkeypatch):
    monkeypatch.delenv("SOURCE_FOLDER", raising=False)
    p = ing.build_arg_parser()
    args = _args(
        p,
        "--mode",
        "domain",
        "--domain",
        "x",
        "--db-path",
        str(tmp_path / "db"),
        "--concept-registry",
        str(tmp_path / "cr.json"),
    )
    (tmp_path / "cr.json").write_text("{}", encoding="utf-8")
    assert ing.ingest_run(args) == 2


def test_main_legacy_code_mode(tmp_path, monkeypatch, patch_ollama_embeddings, concept_registry_path):
    monkeypatch.setenv("EMBEDDING_MODEL", "nomic-embed-text")
    monkeypatch.setenv("SOURCE_FOLDER", str(tmp_path / "c"))
    monkeypatch.setenv("EMBED_WORKERS", "1")
    (tmp_path / "c").mkdir()
    (tmp_path / "c" / "a.py").write_text("x=1\n", encoding="utf-8")
    patch_ollama_embeddings(dim=768)
    db = tmp_path / "vdb"
    rc = ing.main(
        [
            "--db-path",
            str(db),
            "--concept-registry",
            str(concept_registry_path),
            "--force",
        ]
    )
    assert rc == 0


def test_main_requires_mode_or_source(monkeypatch):
    monkeypatch.delenv("SOURCE_FOLDER", raising=False)
    with pytest.raises(SystemExit):
        ing.main(["--db-path", "/tmp", "--concept-registry", "/dev/null"])
