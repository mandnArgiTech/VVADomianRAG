"""STORY C: domain doc ingestion helpers and metadata (ngspice DomainDocs)."""
import json
from pathlib import Path

import pytest

import ingest as ing
import mcp_server


def test_dd01_extract_source_c_files_three_paths():
    md = """# Title

**Source files:**
- `foo/src/spicelib/devices/dio/diodefs.h`
- `/abs/path/dioload.c`
- `rel/other.c`
"""
    s = ing._extract_source_c_files(md)
    assert s == "diodefs.h, dioload.c, other.c"


def test_dd02_extract_source_c_files_empty_without_header():
    assert ing._extract_source_c_files("# Only heading\n\nBody.") == ""


def test_dd03_extract_source_c_files_backticks():
    md = "**Source files:**\n- `a.c`\n"
    assert ing._extract_source_c_files(md) == "a.c"


def test_dd04_chapter_meta_chapter_number():
    m = ing._chapter_meta_from_filename("/x/Chapter_128_Diode_Core_Mathematics_and_DC.md")
    assert m["chapter_number"] == "128"


def test_dd05_chapter_meta_device_family_bsim4():
    m = ing._chapter_meta_from_filename("Chapter_71_BSIM4_Core_Mathematics.md")
    assert m["device_family"] == "BSIM4"


def test_dd06_chapter_meta_ni_core():
    m = ing._chapter_meta_from_filename("Chapter_11_NI_Iteration_Control.md")
    assert m["device_family"] == "CORE"


def test_dd07_protect_math_single_block_survives_split():
    text = "Intro para.\n\n\\[a\n\nb\\]\n\nOutro."
    parts = ing._split_paragraphs(text, 10, 200, protect_math=True)
    joined = "\n\n".join(parts)
    assert "\\[a\n\nb\\]" in joined


def test_dd08_protect_math_multiple_blocks():
    raw = r"x\[1\]y\[2\]z"
    prot, vault = ing._protect_math_blocks(raw)
    assert len(vault) == 2
    out = ing._restore_math_blocks(prot, vault)
    assert r"\[1\]" in out and r"\[2\]" in out


def test_dd09_concept_registry_spice_size():
    reg_path = Path(__file__).resolve().parent.parent / "concept_registry.json"
    data = json.loads(reg_path.read_text(encoding="utf-8"))
    spice = data.get("spice", {})
    assert len(spice) >= 50


def test_dd10_extract_concepts_spice_domain():
    reg = ing.load_concept_registry(Path(__file__).resolve().parent.parent / "concept_registry.json")
    body = "The DEVpnjlim and Jacobian matrix are used in Newton-Raphson."
    cs = ing.extract_concepts(body, "spice", reg)
    ids = set(ing.iter_concept_ids(cs))
    assert "pn_junction_limiter" in ids
    assert "jacobian_matrix" in ids


def test_dd11_chunk_markdown_domain_carries_source_c_files():
    md = """# Doc Title

**Source files:**
- `ngspice/src/x/a.c`

## Section One

First paragraph.

## Section Two

Second.
"""
    chunks = ing.chunk_markdown_domain(md, "Chapter_99_Diode_Test.md")
    assert chunks
    for _t, meta in chunks:
        assert meta.get("source_c_files") == "a.c"
        assert meta.get("chapter_number") == "99"
        assert meta.get("device_family") == "DIO"


def test_dd12_chunk_newton_chapter_reasonable_count():
    path = (
        Path(__file__).resolve().parent.parent
        / "Studio-Portable-RAG"
        / "DomainDocs"
        / "ngspice"
        / "Chapter_04_Newton_Raphson.md"
    )
    if not path.is_file():
        pytest.skip("Chapter_04_Newton_Raphson.md not in tree")
    text = path.read_text(encoding="utf-8")
    chunks = ing.chunk_markdown_domain(text, str(path))
    n = len(chunks)
    assert 3 <= n <= 30


def test_dd13_mcp_format_result_related_sources():
    class _Doc:
        page_content = "body"
        metadata = {
            "section": "Sec",
            "source": "/tmp/x.md",
            "source_c_files": "dioload.c, diodefs.h",
        }

    out = mcp_server.format_result(_Doc(), None, "domain_doc")
    assert "## Related source files" in out
    assert "dioload.c" in out and "diodefs.h" in out


def test_dd14_metadata_keys_contain_source_and_chapter():
    assert "source_c_files" in ing.METADATA_KEYS
    assert "chapter_number" in ing.METADATA_KEYS


def test_domain_doc_content_type_parser_stem():
    assert ing._domain_doc_content_type("Lexical_Analysis_and_Tokens", "CORE") == "parser"


def test_domain_doc_content_type_device_model():
    assert ing._domain_doc_content_type("Core_Math", "BSIM4") == "device_model"


def test_split_paragraphs_protect_math_flag_no_crash():
    t = "A\n\nB"
    assert ing._split_paragraphs(t, 1, 100, protect_math=True)
