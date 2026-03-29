"""Extra branch coverage for ingest_run helpers and tree-sitter shim."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import chromadb
import pytest

import ingest as ing


def test_print_status_with_collection(tmp_vector_db):
    client = chromadb.PersistentClient(path=str(tmp_vector_db))
    coll = client.get_or_create_collection("demo_domain")
    coll.add(
        ids=["1"],
        documents=["hello snmp polling"],
        embeddings=[[0.01] * 768],
        metadatas=[{"source": "/x/a.md", "concepts": "|snmp|", "ingestion_date": "2024-01-01T00:00:00Z"}],
    )
    ing.print_status_dashboard(tmp_vector_db)


def test_parse_rally_filter_malformed():
    assert ing.parse_rally_filter("noseparator") == {}
    assert ing.parse_rally_filter("bad = = x") == {"": ""}


def test_rally_matches_state_string():
    rules = {"state": "Open"}
    assert ing.rally_matches_user_filter({"State": "Open"}, rules)
    assert not ing.rally_matches_user_filter({"State": "Closed"}, rules)


def test_migrate_old_checkpoint_invalid_json(tmp_path):
    old = tmp_path / "ingestion_checkpoint.json"
    old.write_text("not json", encoding="utf-8")
    ing.migrate_old_checkpoint(tmp_path, "c")


def test_migrate_old_checkpoint_not_dict(tmp_path):
    old = tmp_path / "ingestion_checkpoint.json"
    old.write_text("[1,2]", encoding="utf-8")
    ing.migrate_old_checkpoint(tmp_path, "c")


def test_save_checkpoint_nested_dir(tmp_path):
    sub = tmp_path / "a" / "b"
    sub.mkdir(parents=True)
    ing.save_checkpoint(sub, {"x": "y"})
    assert (sub / "ingest_checkpoint.json").exists()


def test_update_repos_manifest_corrupt(tmp_path):
    p = tmp_path / "repos_manifest.json"
    p.write_text("{", encoding="utf-8")
    ing.update_repos_manifest(tmp_path, "c", {"r": 1})


def test_ingest_rally_csv(tmp_path, monkeypatch, patch_ollama_embeddings, concept_registry_path):
    monkeypatch.setenv("EMBEDDING_MODEL", "nomic-embed-text")
    monkeypatch.setenv("EMBED_WORKERS", "1")
    patch_ollama_embeddings(dim=768)
    src = tmp_path / "r"
    src.mkdir()
    csv_content = "FormattedID,Description,Severity,State,Tags\nDE1,%s,2,Open,\n" % ("x" * 300)
    (src / "bugs.csv").write_text(csv_content, encoding="utf-8")
    db = tmp_path / "vdb"
    p = ing.build_arg_parser()
    args = p.parse_args(
        [
            "--mode",
            "rally",
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
    )
    assert ing.ingest_run(args) == 0


def test_ingest_customer_markdown_frontmatter(tmp_path, monkeypatch, patch_ollama_embeddings, concept_registry_path):
    monkeypatch.setenv("EMBEDDING_MODEL", "nomic-embed-text")
    monkeypatch.setenv("EMBED_WORKERS", "1")
    patch_ollama_embeddings(dim=768)
    src = tmp_path / "c"
    src.mkdir()
    body = "---\nsource_platform: x\n---\nCommunity style body " * 20
    (src / "t.md").write_text(body, encoding="utf-8")
    db = tmp_path / "vdb"
    p = ing.build_arg_parser()
    args = p.parse_args(
        [
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
        ]
    )
    assert ing.ingest_run(args) == 0


def test_ingest_mib_keep_deprecated(tmp_path, monkeypatch, patch_ollama_embeddings, concept_registry_path):
    monkeypatch.setenv("EMBEDDING_MODEL", "nomic-embed-text")
    monkeypatch.setenv("EMBED_WORKERS", "1")
    patch_ollama_embeddings(dim=768)
    src = tmp_path / "m"
    src.mkdir()
    mib = """
X DEFINITIONS ::= BEGIN
oldThing OBJECT-TYPE
    SYNTAX INTEGER
    MAX-ACCESS read-only
    STATUS deprecated
    DESCRIPTION "x"
    ::= { x 1 }
END
"""
    (src / "x.mib").write_text(mib, encoding="utf-8")
    db = tmp_path / "vdb"
    p = ing.build_arg_parser()
    args = p.parse_args(
        [
            "--mode",
            "mib",
            "--source",
            str(src),
            "--db-path",
            str(db),
            "--concept-registry",
            str(concept_registry_path),
            "--mib-keep-deprecated",
            "--force",
        ]
    )
    assert ing.ingest_run(args) == 0


def test_ingest_rally_md_text(tmp_path, monkeypatch, patch_ollama_embeddings, concept_registry_path):
    monkeypatch.setenv("EMBEDDING_MODEL", "nomic-embed-text")
    monkeypatch.setenv("EMBED_WORKERS", "1")
    patch_ollama_embeddings(dim=768)
    src = tmp_path / "r"
    src.mkdir()
    (src / "note.md").write_text("Plain rally export " * 50, encoding="utf-8")
    db = tmp_path / "vdb"
    p = ing.build_arg_parser()
    args = p.parse_args(
        [
            "--mode",
            "rally",
            "--domain",
            "utest",
            "--source",
            str(src / "note.md"),
            "--db-path",
            str(db),
            "--concept-registry",
            str(concept_registry_path),
            "--force",
        ]
    )
    assert ing.ingest_run(args) == 0


def test_ingest_rally_json_list(tmp_path, monkeypatch, patch_ollama_embeddings, concept_registry_path):
    monkeypatch.setenv("EMBEDDING_MODEL", "nomic-embed-text")
    monkeypatch.setenv("EMBED_WORKERS", "1")
    patch_ollama_embeddings(dim=768)
    src = tmp_path / "r"
    src.mkdir()
    items = [
        {"FormattedID": "DE1", "Description": "x" * 300, "Severity": "2", "State": "Open"},
        {"FormattedID": "DE2", "Description": "y" * 300, "Severity": "2", "State": "Open"},
    ]
    (src / "list.json").write_text(json.dumps(items), encoding="utf-8")
    db = tmp_path / "vdb"
    p = ing.build_arg_parser()
    args = p.parse_args(
        [
            "--mode",
            "rally",
            "--domain",
            "utest",
            "--source",
            str(src / "list.json"),
            "--db-path",
            str(db),
            "--concept-registry",
            str(concept_registry_path),
            "--force",
        ]
    )
    assert ing.ingest_run(args) == 0


def test_ingest_code_json_config(tmp_path, monkeypatch, patch_ollama_embeddings, concept_registry_path):
    monkeypatch.setenv("EMBEDDING_MODEL", "nomic-embed-text")
    monkeypatch.setenv("EMBED_WORKERS", "1")
    patch_ollama_embeddings(dim=768)
    src = tmp_path / "cfg"
    src.mkdir()
    (src / "c.json").write_text('{"a": 1}\n' * 500, encoding="utf-8")
    db = tmp_path / "vdb"
    p = ing.build_arg_parser()
    args = p.parse_args(
        [
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
        ]
    )
    assert ing.ingest_run(args) == 0


def test_ingest_code_cpp_fallback(tmp_path, monkeypatch, patch_ollama_embeddings, concept_registry_path):
    monkeypatch.setenv("EMBEDDING_MODEL", "nomic-embed-text")
    monkeypatch.setenv("EMBED_WORKERS", "1")
    patch_ollama_embeddings(dim=768)
    src = tmp_path / "cpp"
    src.mkdir()
    (src / "m.cpp").write_text("int main() { return 0; }\n", encoding="utf-8")
    db = tmp_path / "vdb"
    p = ing.build_arg_parser()
    args = p.parse_args(
        [
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
        ]
    )
    assert ing.ingest_run(args) == 0


def test_ingest_code_java(tmp_path, monkeypatch, patch_ollama_embeddings, concept_registry_path):
    monkeypatch.setenv("EMBEDDING_MODEL", "nomic-embed-text")
    monkeypatch.setenv("EMBED_WORKERS", "1")
    patch_ollama_embeddings(dim=768)
    src = tmp_path / "j"
    src.mkdir()
    (src / "A.java").write_text("public class A { void m() {} }\n", encoding="utf-8")
    db = tmp_path / "vdb"
    p = ing.build_arg_parser()
    args = p.parse_args(
        [
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
        ]
    )
    assert ing.ingest_run(args) == 0


def test_ingest_code_js(tmp_path, monkeypatch, patch_ollama_embeddings, concept_registry_path):
    monkeypatch.setenv("EMBEDDING_MODEL", "nomic-embed-text")
    monkeypatch.setenv("EMBED_WORKERS", "1")
    patch_ollama_embeddings(dim=768)
    src = tmp_path / "js"
    src.mkdir()
    (src / "a.js").write_text("function f() { return 1; }\n" * 30, encoding="utf-8")
    db = tmp_path / "vdb"
    p = ing.build_arg_parser()
    args = p.parse_args(
        [
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
        ]
    )
    assert ing.ingest_run(args) == 0


def test_ingest_code_scheme(tmp_path, monkeypatch, patch_ollama_embeddings, concept_registry_path):
    monkeypatch.setenv("EMBEDDING_MODEL", "nomic-embed-text")
    monkeypatch.setenv("EMBED_WORKERS", "1")
    patch_ollama_embeddings(dim=768)
    src = tmp_path / "sc"
    src.mkdir()
    (src / "p.scm").write_text("(define x 1)\n(define y 2)\n", encoding="utf-8")
    db = tmp_path / "vdb"
    p = ing.build_arg_parser()
    args = p.parse_args(
        [
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
        ]
    )
    assert ing.ingest_run(args) == 0


@patch("ingest._fetch_confluence_pages_v2", return_value=None)
@patch("ingest.requests.get")
def test_fetch_confluence_v1_pagination(mock_get, _v2, monkeypatch):
    monkeypatch.setenv("CONFLUENCE_URL", "https://example.atlassian.net")
    monkeypatch.setenv("CONFLUENCE_TOKEN", "tok")
    r1 = MagicMock()
    r1.raise_for_status = MagicMock()
    r1.json.return_value = {
        "results": [
            {
                "status": "current",
                "title": "P1",
                "id": "1",
                "metadata": {"labels": {"results": []}},
                "version": {"when": "t", "by": {"displayName": "U"}},
                "body": {"storage": {"value": "B" * 250}},
            }
        ],
        "_links": {"next": "/wiki/rest/api/content?start=1"},
    }
    r2 = MagicMock()
    r2.raise_for_status = MagicMock()
    r2.json.return_value = {"results": [], "_links": {}}
    mock_get.side_effect = [r1, r2]
    pages = ing.fetch_confluence_pages("SPC", "")
    assert len(pages) >= 1


def test_ts_extract_chunks_c_mocked(monkeypatch):
    class TSNode:
        def __init__(self, t, start, end, children=None):
            self.type = t
            self.start_byte = start
            self.end_byte = end
            self.children = children or []

    class TSTree:
        def __init__(self, root):
            self.root_node = root

    class TSParser:
        def parse(self, data):
            root = TSNode("translation_unit", 0, len(data), [TSNode("function_definition", 0, min(12, len(data)))])
            return TSTree(root)

    monkeypatch.setattr(ing, "_ts_parser_for", lambda _ln, _mn: TSParser())
    p = Path("t.c")
    content = "int main(){}"
    out = ing._ts_extract_chunks(p, content, "c")
    assert out is not None and len(out) >= 1


def test_ts_extract_unknown_grammar():
    assert ing._ts_extract_chunks(Path("x.c"), "x", "zig") is None


def test_feed_domain_chunk_index_valueerror(tmp_path, monkeypatch, fake_embedder):
    monkeypatch.setattr(ing, "OllamaEmbeddings", lambda **kw: fake_embedder)

    def fake_md(*a, **k):
        return [("t", {"chunk_index": "bad", "section": "s"})]

    monkeypatch.setattr(ing, "chunk_markdown_domain", fake_md)
    f = tmp_path / "d.md"
    f.write_text("# X\n", encoding="utf-8")
    reg = tmp_path / "cr.json"
    reg.write_text("{}", encoding="utf-8")
    ing.feed_domain_document(
        str(f),
        "utest",
        str(tmp_path / "db"),
        "nomic-embed-text",
        concept_registry_path=str(reg),
        source_type="domain_doc",
    )
