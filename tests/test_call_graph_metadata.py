"""Call-graph metadata and MCP callee expansion (Story B)."""
from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from langchain_core.documents import Document

import ingest as ing
import mcp_server as mcp


def _have_tree_sitter_c() -> bool:
    return all(importlib.util.find_spec(x) is not None for x in ("tree_sitter", "tree_sitter_c"))


def _have_tree_sitter_cpp() -> bool:
    return all(importlib.util.find_spec(x) is not None for x in ("tree_sitter", "tree_sitter_cpp"))


skip_without_ts_c = pytest.mark.skipif(
    not _have_tree_sitter_c(),
    reason="tree-sitter C not installed",
)

skip_without_ts_cpp = pytest.mark.skipif(
    not _have_tree_sitter_cpp(),
    reason="tree-sitter C++ not installed",
)


def test_cg10_calls_in_metadata_keys():
    assert "calls" in ing.METADATA_KEYS


def test_cg17_pipe_roundtrip():
    assert ing.format_concepts_field(["alpha", "beta"]) == "|alpha|beta|"
    assert ing.iter_concept_ids("|alpha|beta|") == ["alpha", "beta"]


def test_cg07_py_calls_name_and_attr():
    tree = ast.parse(
        "def foo():\n    bar()\n    baz.qux()\n"
    )
    fn = tree.body[0]
    assert isinstance(fn, ast.FunctionDef)
    calls = ing._extract_py_calls(fn)
    assert "bar" in calls
    assert "qux" in calls


def test_cg08_py_skips_builtins():
    tree = ast.parse("def foo():\n    x = len(items)\n    process(x)\n")
    fn = tree.body[0]
    calls = ing._extract_py_calls(fn)
    assert calls == ["process"]


def test_cg09_py_self_methods():
    tree = ast.parse(
        "def foo(self):\n    self._nr_loop()\n    self.solve()\n"
    )
    fn = tree.body[0]
    calls = ing._extract_py_calls(fn)
    assert "_nr_loop" in calls
    assert "solve" in calls


def test_cg_format_calls_truncation():
    many = [f"f{i}" for i in range(55)]
    s = ing._format_calls_metadata(many)
    assert "__truncated__" in s
    ids = ing.iter_concept_ids(s)
    assert len([x for x in ids if x != "__truncated__"]) <= 50


@skip_without_ts_c
def test_cg01_c_simple_calls(tmp_path: Path):
    src = "void foo() { bar(); baz(); }\n"
    path = tmp_path / "t.c"
    path.write_text(src, encoding="utf-8")
    chunks = ing._ts_extract_chunks(path, src, "c")
    assert chunks
    fn_chunk = next(c for c in chunks if c[1].get("chunk_type") == "function_definition")
    meta = fn_chunk[1]
    raw = meta.get("calls") or ""
    ids = ing.iter_concept_ids(raw)
    assert "bar" in ids
    assert "baz" in ids


@skip_without_ts_c
def test_cg02_c_skips_stdlib(tmp_path: Path):
    src = "void foo() { malloc(10); CKTload(ckt); free(p); }\n"
    path = tmp_path / "t.c"
    path.write_text(src, encoding="utf-8")
    chunks = ing._ts_extract_chunks(path, src, "c")
    fn_chunk = next(c for c in chunks if c[1].get("chunk_type") == "function_definition")
    ids = ing.iter_concept_ids(fn_chunk[1].get("calls") or "")
    assert "CKTload" in ids
    assert "malloc" not in ids
    assert "free" not in ids


@skip_without_ts_c
def test_cg03_field_expression(tmp_path: Path):
    src = "void foo() { ckt->CKTload(ckt); }\n"
    path = tmp_path / "t.c"
    path.write_text(src, encoding="utf-8")
    chunks = ing._ts_extract_chunks(path, src, "c")
    fn_chunk = next(c for c in chunks if c[1].get("chunk_type") == "function_definition")
    ids = ing.iter_concept_ids(fn_chunk[1].get("calls") or "")
    assert "CKTload" in ids


@skip_without_ts_c
def test_cg04_no_calls(tmp_path: Path):
    src = "int answer() { return 42; }\n"
    path = tmp_path / "t.c"
    path.write_text(src, encoding="utf-8")
    chunks = ing._ts_extract_chunks(path, src, "c")
    fn_chunk = next(c for c in chunks if c[1].get("chunk_type") == "function_definition")
    assert not (fn_chunk[1].get("calls") or "").strip()


@skip_without_ts_c
def test_cg05_nested_calls(tmp_path: Path):
    src = "void foo() { alpha(beta(gamma())); }\n"
    path = tmp_path / "t.c"
    path.write_text(src, encoding="utf-8")
    chunks = ing._ts_extract_chunks(path, src, "c")
    fn_chunk = next(c for c in chunks if c[1].get("chunk_type") == "function_definition")
    ids = ing.iter_concept_ids(fn_chunk[1].get("calls") or "")
    assert set(ids) >= {"alpha", "beta", "gamma"}


@skip_without_ts_cpp
def test_cg_cpp_function_calls(tmp_path: Path):
    src = "void foo() { bar(); baz(); }\n"
    path = tmp_path / "t.cpp"
    path.write_text(src, encoding="utf-8")
    chunks = ing._ts_extract_chunks(path, src, "cpp")
    assert chunks
    fn_chunk = next(c for c in chunks if c[1].get("chunk_type") == "function_definition")
    ids = ing.iter_concept_ids(fn_chunk[1].get("calls") or "")
    assert "bar" in ids and "baz" in ids


@skip_without_ts_c
def test_cg12_struct_empty_calls(tmp_path: Path):
    src = "struct S { int x; };\n"
    path = tmp_path / "t.c"
    path.write_text(src, encoding="utf-8")
    chunks = ing._ts_extract_chunks(path, src, "c")
    st = next(c for c in chunks if c[1].get("chunk_type") == "struct_specifier")
    assert not (st[1].get("calls") or "").strip()


def test_cg11_python_function_has_calls_metadata(tmp_path: Path):
    p = tmp_path / "m.py"
    p.write_text("def foo():\n    bar()\n", encoding="utf-8")
    chunks = ing.ast_chunk_python(p, p.read_text(encoding="utf-8"))
    fn = next(c for c in chunks if c[1].get("chunk_type") == "function")
    raw = fn[1].get("calls") or ""
    assert "bar" in ing.iter_concept_ids(raw)


def test_cg13_sync_fetch_callees_finds_chunk(monkeypatch):
    monkeypatch.delenv("RAG_CALLEE_EXPAND", raising=False)
    primary_doc = Document(
        page_content="caller",
        metadata={
            "calls": "|CKTload|",
            "repository": "ngspice",
            "source": "/x/a.c",
            "relative_path": "a.c",
            "chunk_name": "caller",
            "chunk_index": "0",
        },
    )
    callee_meta = {
        "repository": "ngspice",
        "source": "/x/b.c",
        "relative_path": "b.c",
        "chunk_name": "CKTload",
        "chunk_index": "1",
        "extension": ".c",
    }
    matches = {
        "CKTload": [{"id": "id1", "doc": "void CKTload() {}", "meta": callee_meta}],
    }

    def getter(where=None, limit=None, include=None):
        callee = where["chunk_name"]["$eq"]
        rows = matches.get(callee, [])
        return {
            "ids": [r["id"] for r in rows],
            "documents": [r["doc"] for r in rows],
            "metadatas": [r["meta"] for r in rows],
        }

    col = MagicMock()
    col.get.side_effect = getter

    vs = MagicMock()
    vs._collection = col
    cmap = {"spice_code": vs}
    out = mcp._sync_fetch_callees(
        [(primary_doc, 0.1, "code")],
        cmap,
        "code",
        "spice",
        "",
        10,
    )
    assert len(out) == 1
    assert out[0][2] == "callee"
    assert "CKTload" in (out[0][0].metadata or {}).get("chunk_name", "")


def test_cg14_respects_max_callees(monkeypatch):
    monkeypatch.delenv("RAG_CALLEE_EXPAND", raising=False)

    names = [f"n{i}" for i in range(20)]
    calls_field = ing.format_concepts_field(names)
    primary_doc = Document(
        page_content="x",
        metadata={
            "calls": calls_field,
            "repository": "r",
            "source": "s",
            "relative_path": "a.c",
            "chunk_name": "f",
            "chunk_index": "0",
        },
    )

    def getter(where=None, limit=None, include=None):
        callee = where["chunk_name"]["$eq"]
        return {
            "ids": [callee],
            "documents": [f"body {callee}"],
            "metadatas": [
                {
                    "chunk_name": callee,
                    "repository": "r",
                    "source": "s",
                    "relative_path": f"{callee}.c",
                    "chunk_index": "0",
                }
            ],
        }

    col = MagicMock()
    col.get.side_effect = getter
    vs = MagicMock()
    vs._collection = col
    cmap = {"spice_code": vs}
    out = mcp._sync_fetch_callees(
        [(primary_doc, 0.1, "code")],
        cmap,
        "code",
        "spice",
        "",
        5,
    )
    assert len(out) == 5


def test_cg15_dedup_primary_already_has_callee(monkeypatch):
    monkeypatch.delenv("RAG_CALLEE_EXPAND", raising=False)
    meta = {
        "calls": "|CKTload|",
        "repository": "r",
        "source": "/same",
        "relative_path": "a.c",
        "chunk_name": "CKTload",
        "chunk_index": "0",
    }
    primary_doc = Document(page_content="already", metadata=dict(meta))
    col = MagicMock()
    col.get.return_value = {
        "ids": ["id1"],
        "documents": ["dup"],
        "metadatas": [dict(meta)],
    }
    vs = MagicMock()
    vs._collection = col
    cmap = {"spice_code": vs}
    out = mcp._sync_fetch_callees(
        [(primary_doc, 0.1, "code")],
        cmap,
        "code",
        "spice",
        "",
        10,
    )
    assert out == []


def test_cg16_expand_disabled(monkeypatch):
    monkeypatch.setenv("RAG_CALLEE_EXPAND", "0")
    out = mcp._sync_fetch_callees([], {}, "code", "spice", "", 10)
    assert out == []


def test_cg18_repo_filter_excludes_other_repo(monkeypatch):
    monkeypatch.delenv("RAG_CALLEE_EXPAND", raising=False)
    primary_doc = Document(
        page_content="x",
        metadata={
            "calls": "|foo|",
            "repository": "repo_a",
            "source": "s",
            "relative_path": "a.c",
            "chunk_name": "f",
            "chunk_index": "0",
        },
    )

    def getter(where=None, limit=None, include=None):
        return {
            "ids": ["1"],
            "documents": ["body"],
            "metadatas": [
                {
                    "chunk_name": "foo",
                    "repository": "repo_b",
                    "source": "s",
                    "relative_path": "b.c",
                    "chunk_index": "0",
                }
            ],
        }

    col = MagicMock()
    col.get.side_effect = getter
    vs = MagicMock()
    vs._collection = col
    cmap = {"spice_code": vs}
    out = mcp._sync_fetch_callees(
        [(primary_doc, 0.1, "code")],
        cmap,
        "code",
        "spice",
        "repo_a",
        10,
    )
    assert out == []
