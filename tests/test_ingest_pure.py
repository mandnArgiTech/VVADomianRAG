"""Unit tests for pure helpers and chunk strategies in ingest.py."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from langchain_text_splitters import Language

import ingest as ing


def test_setup_logging_no_crash():
    ing.setup_logging(False)
    ing.setup_logging(True)


def test_make_chunk_id_deterministic():
    a = ing.make_chunk_id("/x/a.py", 0, "hello")
    b = ing.make_chunk_id("/x/a.py", 0, "hello")
    assert a == b
    assert a != ing.make_chunk_id("/x/a.py", 1, "hello")


def test_resolve_collection():
    assert ing.resolve_collection("domain", "igmp", None) == "igmp_domain"
    assert ing.resolve_collection("code", "igmp", None) == "igmp_code"
    assert ing.resolve_collection("rfc", "x", None) == "rfc"
    assert ing.resolve_collection("domain", "igmp", "custom") == "custom"


def test_empty_finalize_metadata():
    e = ing.empty_metadata()
    assert all(v == "" for v in e.values())
    m = ing.finalize_metadata({"source": "x", "unknown": 1})
    assert m["source"] == "x"
    assert "unknown" not in m or m.get("unknown") == ""


def test_detect_content_type():
    assert ing.detect_content_type("the algorithm process flow steps") == "algorithm"
    assert ing.detect_content_type("random text without signals") == "general"


def test_load_concept_registry_missing(tmp_path):
    reg = ing.load_concept_registry(tmp_path / "nope.json")
    assert "nms" in reg and "vlan" in reg["nms"]


def test_load_concept_registry_valid(tmp_path):
    p = tmp_path / "c.json"
    p.write_text('{"d": {"k": "a,b"}}', encoding="utf-8")
    reg = ing.load_concept_registry(p)
    assert "d" in reg


def test_extract_concepts_and_iter():
    reg = {"nms": {"snmp": "snmp,oid"}}
    s = ing.extract_concepts("The SNMP agent uses OID 1.3.6", "nms", reg)
    assert "snmp" in s or "|" in s
    ids = list(ing.iter_concept_ids("|snmp|oid|"))
    assert "snmp" in ids
    assert ing.format_concepts_field([]) == ""
    assert ing.format_concepts_field(["a", "b"]) == "|a|b|"


def test_extract_concepts_word_boundaries_spice():
    """Ngspice plan: avoid substring false positives (e.g. token inside another word)."""
    reg = {
        "spice": {
            "CKT": "circuit_struct",
            "cap": "capacitor_device",
            "Newton-Raphson": "newton_raphson_solver",
        }
    }
    assert ing.extract_concepts("myescape variable", "spice", reg) == ""
    assert "circuit_struct" in ing.extract_concepts("the CKT struct field", "spice", reg)
    assert "capacitor_device" not in ing.extract_concepts("escape hatch", "spice", reg)
    assert "newton_raphson_solver" in ing.extract_concepts(
        "using Newton-Raphson iteration", "spice", reg
    )


def test_write_ngspice_gitignore_unreadable_existing_still_appends(tmp_path, monkeypatch):
    src = tmp_path / "ng"
    src.mkdir()
    gi = src / ".gitignore"
    gi.write_text("keep-me\n", encoding="utf-8")
    real_read = Path.read_text

    def fake_read(self, *args, **kwargs):
        if self.resolve() == gi.resolve():
            raise OSError("denied")
        return real_read(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fake_read)
    ing.write_ngspice_gitignore(src)
    with open(gi, encoding="utf-8") as fh:
        text = fh.read()
    assert "keep-me" in text
    assert "Ngspice legacy boilerplate" in text
    assert "src/frontend/" in text


def test_read_file_bytes_and_md5(tmp_path):
    p = tmp_path / "f.bin"
    p.write_bytes(b"\xff\xfeabc")
    content, enc = ing.read_file_bytes(p)
    assert content is not None
    h = ing.file_md5(p)
    assert len(h) == 32


def test_strip_html_bs4():
    t = ing.strip_html("<p>Hi <b>there</b></p>")
    assert "Hi" in t


def test_strip_html_regex_fallback(monkeypatch):
    monkeypatch.setattr(ing, "BeautifulSoup", None)
    t = ing.strip_html("<p>x</p>")
    assert "x" in t


def test_safe_count():
    class C:
        def count(self):
            return 3

    assert ing._safe_count(C()) == 3


def test_parse_rally_filter_and_match():
    rules = ing.parse_rally_filter("severity=1,2 state=Open")
    assert "severity" in rules
    obj = {"Severity": "2", "State": "Open"}
    assert ing.rally_matches_user_filter(obj, rules)
    assert not ing.rally_matches_user_filter({"Severity": "9", "State": "Open"}, rules)


def test_mask_bare_mermaid_block():
    md = "## Flow\n\ngraph TD\n  A[Start] --> B[End]\n\n## Next\n\nText.\n"
    masked, vault = ing._mask_markdown_fences_and_tables(md)
    assert "graph TD" not in masked
    assert vault and any("Flowchart" in (b.diagram_type or "") for b in vault)


def test_mask_unmask_markdown_and_types():
    md = "```mermaid\nsequenceDiagram\n  A->>B: x\n```\n\n|a|b|\n|---|---|\n|1|2|\n"
    masked, vault = ing._mask_markdown_fences_and_tables(md)
    assert "<<BLOCK" in masked
    txt, has_d, label = ing._unmask_markdown_with_meta("Intro\n\n<<BLOCK0>>", vault)
    assert has_d
    assert "Metadata" in txt


def test_split_paragraphs_diagram_bond():
    body = "Para one.\n\n<<BLOCK0>>\n\nPara two."
    parts = ing._split_paragraphs(body, 100, 400)
    assert any("<<BLOCK0>>" in p for p in parts)


def test_md_rfc_char_targets_and_estimate():
    mn, mx = ing._md_char_targets("mxbai-embed-large")
    assert mn < mx
    assert ing._estimate_tokens("abcd") >= 1
    assert ing._get_rfc_token_limit("nomic-embed-text") == 8192


def test_is_rfc_file(tmp_path):
    assert ing._is_rfc_file(tmp_path / "rfc793.txt")
    assert not ing._is_rfc_file(tmp_path / "readme.md")


def test_depaginate_rfc():
    raw = "RFC 793\n\n\f\n\n[Page 2]\n\nBody line.\n"
    out = ing._depaginate_rfc(raw)
    assert "Page 2" not in out or "Body" in out


def test_rfc_line_is_diagram():
    assert ing._rfc_line_is_diagram("    |----+----|")
    assert not ing._rfc_line_is_diagram("Plain text.")


def test_sliding_window_chunks():
    text = "Para one.\n\nPara two.\n\nPara three.\n\n" * 20
    chunks = ing._sliding_window_chunks(text, 200, 0.1, {"chunk_strategy": "test"})
    assert len(chunks) >= 2


def test_chunk_markdown_domain_small(tmp_path):
    p = tmp_path / "d.md"
    md = "# Title\n\n## Sec\n\nHello world.\n"
    p.write_text(md, encoding="utf-8")
    parts = ing.chunk_markdown_domain(md, str(p), embed_model="nomic-embed-text")
    assert parts


def test_chunk_rfc_minimal():
    text = """
Network Working Group
Request for Comments: 9999

Example RFC Title

1. INTRO

This is the introduction with enough text.

2. DETAIL

More detail here.
"""
    parts = ing.chunk_rfc(text, "/tmp/rfc9999.txt", embed_model="mxbai-embed-large")
    assert parts


def test_chunk_rally_ticket():
    obj = {
        "FormattedID": "DE123",
        "Name": "Bug",
        "Description": "<p>Desc</p>",
        "Resolution": "",
        "Discussion": "",
        "Severity": "2",
    }
    parts = ing.chunk_rally_ticket(obj, "src")
    assert parts and parts[0][0]


def test_chunk_customer_ticket():
    obj = {"ticket_id": "T1", "subject": "S", "description": "D"}
    parts = ing.chunk_customer_ticket(obj, "src")
    assert parts


def test_chunk_mib_sample():
    mib = """
IF-MIB DEFINITIONS ::= BEGIN
imported OBJECT IDENTIFIER ::= { iso 1 }
myScalar OBJECT-TYPE
    SYNTAX INTEGER
    MAX-ACCESS read-only
    STATUS current
    DESCRIPTION "test"
    ::= { interfaces 1 }
END
"""
    parts = ing.chunk_mib(mib, Path("IF-MIB.mib"), skip_deprecated=True)
    assert parts


def test_chunk_mib_deprecated_skipped():
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
    parts = ing.chunk_mib(mib, Path("X.mib"), skip_deprecated=True)
    assert parts[0][1].get("chunk_type") == "mib_file"


def test_chunk_release_notes():
    text = "# 1.0.0\n\n## New Features\n\nCool stuff.\n\n# 1.0.1\n\n## Bug Fixes\n\nFixed.\n"
    parts = ing.chunk_release_notes(text, "REL.md")
    assert len(parts) >= 1


def test_parse_frontmatter_chunk_community():
    fm, body = ing.parse_frontmatter("---\na: b\n---\nBody")
    assert fm.get("a") == "b"
    assert "Body" in body
    parts = ing.chunk_community("Short body", "p", {"source_platform": "so"})
    assert len(parts) == 1


def test_chunk_wiki_page():
    html = "<html><body><h1>T</h1><p>Paragraph text here.</p></body></html>"
    parts = ing.chunk_wiki_page(
        html,
        "u",
        {"page_title": "T", "space": "S", "labels": "", "author": "", "parent_page": "", "page_url": "", "last_modified": ""},
        embed_model="nomic-embed-text",
    )
    assert parts


def test_language_split_and_generic(tmp_path):
    p = tmp_path / "x.md"
    p.write_text("# H\n\n" + ("line\n" * 50), encoding="utf-8")
    c = p.read_text(encoding="utf-8")
    parts = ing.language_split(p, c, Language.MARKDOWN)
    assert parts
    parts2 = ing.generic_split(c, p, 500)
    assert parts2


def test_ast_chunk_python_ok_and_syntax_error(tmp_path):
    p = tmp_path / "m.py"
    good = "def f():\n    return 1\n\nclass C:\n    pass\n"
    p.write_text(good, encoding="utf-8")
    parts = ing.ast_chunk_python(p, good)
    assert len(parts) >= 1
    bad = "def broken(\n"
    parts_bad = ing.ast_chunk_python(p, bad)
    assert parts_bad


def test_ts_extract_chunks_mocked(tmp_path):
    p = tmp_path / "f.c"
    p.write_text("int main(){return 0;}", encoding="utf-8")
    fake = [("chunk", {"chunk_strategy": "ast_c", "chunk_type": "x", "chunk_name": "m", "chunk_index": "0"})]
    with patch.object(ing, "_ts_extract_chunks", return_value=fake):
        st, fn, lim, _ov = ing.choose_strategy_for_path(p, "code")
        assert st == "code"
        assert _ov is None
        out = fn(p, p.read_text())
        assert out == fake


def test_choose_strategy_matrix(tmp_path):
    py = tmp_path / "a.py"
    py.write_text("x=1", encoding="utf-8")
    st, fn, _, _ov = ing.choose_strategy_for_path(py, "code")
    assert st == "code"
    assert _ov is None
    md = tmp_path / "b.md"
    md.write_text("# T\n\nx", encoding="utf-8")
    st2, fn2, _, _ov2 = ing.choose_strategy_for_path(md, "domain_doc")
    assert st2 == "domain_doc"
    assert _ov2 is None
    rfc = tmp_path / "rfc1.txt"
    rfc.write_text("1. X\n\ny", encoding="utf-8")
    st3, fn3, _, _ov3 = ing.choose_strategy_for_path(rfc, "rfc", embed_model="nomic-embed-text")
    assert st3 == "rfc"
    assert _ov3 is None


def test_device_family_for_path():
    assert ing._device_family_for_path(Path("a/b/devices/bjt/load.c")) == "BJT"
    assert ing._device_family_for_path(Path("devices/bsim4/x.c")) == "BSIM4"
    assert ing._device_family_for_path(Path("src/foo.c")) == "CORE"


def test_is_ngspice_manual_doc_path(tmp_path):
    p = tmp_path / "docs" / "a.rst"
    p.parent.mkdir(parents=True)
    p.write_text("x", encoding="utf-8")
    assert ing._is_ngspice_manual_doc_path(p)
    assert not ing._is_ngspice_manual_doc_path(tmp_path / "docs" / "b.c")
    plain = tmp_path / "readme.md"
    plain.write_text("x", encoding="utf-8")
    assert not ing._is_ngspice_manual_doc_path(plain)


def test_ngspice_manual_choose_strategy(tmp_path):
    p = tmp_path / "Spice64" / "docs" / "chap.md"
    p.parent.mkdir(parents=True)
    p.write_text("# Ch\n", encoding="utf-8")
    st, _fn, lim, ov = ing.choose_strategy_for_path(p, "code")
    assert st == "code" and ov == "ngspice_manual"
    assert lim == ing.STRATEGY_SIZE_LIMIT_MB["domain_doc"]


def test_core_constant_preproc_in_cktdefs(tmp_path):
    pytest.importorskip("tree_sitter")
    p = tmp_path / "cktdefs.h"
    p.write_text("#define CKT_TYPE 1\n", encoding="utf-8")
    out = ing._ts_extract_chunks(p, p.read_text(encoding="utf-8"), "c")
    if out is None:
        pytest.skip("tree-sitter C parser unavailable")
    assert any(m.get("chunk_type") == "core_constant" for _, m in out)


def test_chunk_scheme_regex(tmp_path):
    p = tmp_path / "s.scm"
    content = "(define foo 1)\n(define bar 2)\n"
    parts = ing.chunk_scheme(content, p)
    assert parts


def test_sentence_window(tmp_path):
    p = tmp_path / "n.md"
    text = "# T\n\n" + "word " * 200
    parts = ing.sentence_window(text, p)
    assert len(parts) >= 1


def test_js_ts_lang():
    exp = getattr(Language, "TS", getattr(Language, "TYPESCRIPT", Language.HTML))
    assert ing._js_ts_lang(".tsx") == exp
    exp_js = getattr(Language, "JS", getattr(Language, "JAVASCRIPT", Language.HTML))
    assert ing._js_ts_lang(".js") == exp_js


def test_extract_release_date():
    assert ing._extract_release_date_near_version("Released: 2024-01-15") != ""


def test_ts_comment_prefix():
    c = "// hi\n/* x */\nint a;"
    assert "hi" in ing._ts_comment_prefix(c, len(c) - 6, 2) or ing._ts_comment_prefix(c, len(c) - 6, 2) == ""


def test_unshield_diagrams():
    text, vault = ing._shield_diagrams("Line\n  +---+\n  | x |\n  +---+\nTail")
    restored = ing._unshield_diagrams(text, vault)
    assert "+" in restored or "Line" in restored


def test_diagram_vault_sort_key():
    assert ing._diagram_vault_sort_key("__DIAGRAM_12__") == 12


def test_iter_files_single_and_walk(tmp_path):
    f = tmp_path / "a.py"
    f.write_text("x", encoding="utf-8")
    assert len(ing.iter_files(f, None, skip_dirs=ing.IGNORED_DIRS)) == 1
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "b.mib").write_text("X", encoding="utf-8")
    xs = ing.iter_files(tmp_path, {".mib"}, skip_dirs=ing.IGNORED_DIRS)
    assert any(p.suffix == ".mib" for p in xs)


def test_iter_concept_ids_comma_form():
    assert ing.iter_concept_ids("a, b, c") == ["a", "b", "c"]


def test_iter_files_skip_ext(tmp_path):
    (tmp_path / "a.exe").write_bytes(b"")
    out = ing.iter_files(tmp_path, None, skip_dirs=set(), skip_exts={".exe"})
    assert not out


def test_print_status_dashboard_empty_db(tmp_vector_db, capsys):
    ing.print_status_dashboard(tmp_vector_db)
    captured = capsys.readouterr()
    assert "DOMAIN RAG" in captured.out


def test_build_arg_parser():
    p = ing.build_arg_parser()
    args = p.parse_args(["--mode", "status", "--db-path", "/tmp"])
    assert args.mode == "status"


def test_choose_strategy_mib_wiki_community_release(tmp_path):
    mib = tmp_path / "m.mib"
    mib.write_text("X DEFINITIONS ::= BEGIN END\n", encoding="utf-8")
    st, fn, _, _ov = ing.choose_strategy_for_path(mib, "mib")
    assert st == "mib"
    assert _ov is None
    assert fn(mib, mib.read_text(encoding="utf-8"))

    md = tmp_path / "w.md"
    md.write_text("# W\n", encoding="utf-8")
    st_w, fn_w, _, _ovw = ing.choose_strategy_for_path(md, "wiki")
    assert st_w == "wiki"
    assert _ovw is None

    st_c, fn_c, _, _ovc = ing.choose_strategy_for_path(md, "community")
    assert st_c == "community"
    assert _ovc is None

    st_r, fn_r, _, _ovr = ing.choose_strategy_for_path(md, "release_notes")
    assert st_r == "release_notes"
    assert _ovr is None

    binf = tmp_path / "u.unknownext"
    binf.write_text("z" * 100, encoding="utf-8")
    st_d, _, _, _ovd = ing.choose_strategy_for_path(binf, "nosuch")
    assert st_d == "default"
    assert _ovd is None

    st_th, _, _, _ovth = ing.choose_strategy_for_path(md, "theory")
    assert st_th == "theory"
    assert _ovth is None
