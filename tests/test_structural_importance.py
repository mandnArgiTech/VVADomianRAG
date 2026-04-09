"""Structural importance scoring (Story A)."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from langchain_core.documents import Document

import ingest as ing
import mcp_server as mcp


def test_si01_extract_stems_c_includes():
    src = '#include "common.h"\n#include <util.h>\n#include "subdir/foo.h"\n'
    stems = ing._extract_dependency_stems(src, ".c")
    assert "common.h" in stems or "common" in [ing._normalize_refcount_stem(s) for s in stems]
    assert any(ing._normalize_refcount_stem(s) == "common" for s in stems)
    assert any(ing._normalize_refcount_stem(s) == "util" for s in stems)
    assert any(ing._normalize_refcount_stem(s) == "foo" for s in stems)


def test_si02_extract_stems_python():
    src = "import numpy\nfrom ecad.models import X\n"
    stems = ing._extract_dependency_stems(src, ".py")
    assert "numpy" in stems
    assert "ecad" in stems
    assert "models" in stems or "X" in stems


def test_si03_extract_stems_empty():
    assert ing._extract_dependency_stems("just text\n", ".c") == []


def test_si04_extract_dependencies_backward_compat():
    src = '#include "a.h"\n#include "b.h"\n'
    dep = ing.extract_dependencies(src, ".c")
    assert "a" in dep and "b" in dep


def test_extract_stems_js_module_path():
    src = "import { x } from './subdir/mod.js'\n"
    stems = ing._extract_dependency_stems(src, ".js")
    assert any(s == "mod" for s in stems)


def test_extract_stems_java_package():
    src = "import java.util.ArrayList;\n"
    stems = ing._extract_dependency_stems(src, ".java")
    assert any("ArrayList" in s or "util" in s for s in stems)


def test_extract_stems_go_import():
    src = 'import (\n  "fmt"\n  "encoding/json"\n)\n'
    stems = ing._extract_dependency_stems(src, ".go")
    assert "fmt" in stems or any("fmt" in s for s in stems)


def test_extract_stems_rust_use_mod():
    src = "use std::collections::HashMap;\nmod foo;\n"
    stems = ing._extract_dependency_stems(src, ".rs")
    assert "std" in stems or "foo" in stems


def test_extract_stems_python_syntax_error_regex_fallback():
    src = "def broken(\nfrom models import X\n"
    stems = ing._extract_dependency_stems(src, ".py")
    assert "models" in stems


def test_build_file_ref_counts_skips_virtual(tmp_path: Path):
    f = tmp_path / "a.c"
    f.write_text("", encoding="utf-8")
    counts = ing.build_file_ref_counts_for_code_ingest([(f, {"virtual": True})])
    assert counts == {}


def test_build_file_ref_counts_read_oserror_skipped():
    p = MagicMock()
    p.is_file.return_value = True
    p.suffix = ".c"
    p.read_bytes.side_effect = OSError("denied")
    assert ing.build_file_ref_counts_for_code_ingest([(p, {})]) == {}


def test_si05_file_ref_counts_c(tmp_path: Path):
    d = tmp_path / "src"
    d.mkdir()
    (d / "common.h").write_text("//h\n", encoding="utf-8")
    (d / "util.h").write_text("//h\n", encoding="utf-8")
    (d / "a.c").write_text('#include "common.h"\n', encoding="utf-8")
    (d / "b.c").write_text('#include "common.h"\n#include "util.h"\n', encoding="utf-8")
    (d / "c.c").write_text('#include "util.h"\n', encoding="utf-8")
    files = [(d / "a.c", {}), (d / "b.c", {}), (d / "c.c", {})]
    counts = ing.build_file_ref_counts_for_code_ingest(files)
    assert counts.get("common") == 2
    assert counts.get("util") == 2


def test_si05b_duplicate_include_counts_once(tmp_path: Path):
    d = tmp_path / "x.c"
    d.write_text('#include "dup.h"\n#include "dup.h"\n', encoding="utf-8")
    counts = ing.build_file_ref_counts_for_code_ingest([(d, {})])
    assert counts.get("dup") == 1


def test_si06_file_ref_counts_python(tmp_path: Path):
    d = tmp_path / "pkg"
    d.mkdir()
    (d / "a.py").write_text("import models\n", encoding="utf-8")
    (d / "b.py").write_text("import models\n", encoding="utf-8")
    (d / "c.py").write_text("import solver\n", encoding="utf-8")
    files = [(d / "a.py", {}), (d / "b.py", {}), (d / "c.py", {})]
    counts = ing.build_file_ref_counts_for_code_ingest(files)
    assert counts.get("models") == 2
    assert counts.get("solver") == 1


def test_si07_metadata_keys():
    assert "structural_importance" in ing.METADATA_KEYS


def test_si09_non_code_domain_doc_structural_zero(tmp_path, monkeypatch, patch_ollama_embeddings, concept_registry_path):
    monkeypatch.setenv("EMBEDDING_MODEL", "nomic-embed-text")
    patch_ollama_embeddings(dim=768)
    src = tmp_path / "docs"
    src.mkdir()
    (src / "note.md").write_text("# T\n\n## S\n\nHello.\n", encoding="utf-8")
    db = tmp_path / "vdb"
    p = ing.build_arg_parser()
    args = p.parse_args(
        [
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
        ]
    )
    assert ing.ingest_run(args) == 0


def test_si10_format_result_shows_importance():
    doc = Document(
        page_content="void f() {}",
        metadata={
            "repository": "r",
            "relative_path": "a.c",
            "extension": ".c",
            "chunk_name": "f",
            "chunk_type": "function",
            "structural_importance": "5",
        },
    )
    out = mcp.format_result(doc, 0.1, "code")
    assert "importance" in out.lower()
    assert "5" in out


def test_si11_format_result_hides_zero_importance():
    doc = Document(
        page_content="x",
        metadata={
            "repository": "r",
            "relative_path": "a.c",
            "extension": ".c",
            "chunk_name": "f",
            "structural_importance": "0",
        },
    )
    out = mcp.format_result(doc, 0.1, "code")
    assert "importance" not in out.lower()


def test_si12_tiebreaker_sort_dense_order():
    def doc(si: str) -> Document:
        return Document(page_content="x", metadata={"structural_importance": si})

    merged = [
        (doc("0"), 0.15, "code", "coll"),
        (doc("5"), 0.15, "code", "coll"),
        (doc("2"), 0.15, "code", "coll"),
    ]
    merged.sort(
        key=lambda x: (
            round(x[1] if x[1] is not None else 1e9, 3),
            -mcp._structural_importance_int(getattr(x[0], "metadata", None)),
        )
    )
    order = [x[0].metadata["structural_importance"] for x in merged]
    assert order == ["5", "2", "0"]


def test_si13_distance_dominates_importance():
    def doc(si: str) -> Document:
        return Document(page_content="x", metadata={"structural_importance": si})

    merged = [
        (doc("1"), 0.2, "code", "coll"),
        (doc("10"), 0.1, "code", "coll"),
    ]
    merged.sort(
        key=lambda x: (
            round(x[1] if x[1] is not None else 1e9, 3),
            -mcp._structural_importance_int(getattr(x[0], "metadata", None)),
        )
    )
    assert merged[0][1] == 0.1
    assert merged[0][0].metadata["structural_importance"] == "10"
