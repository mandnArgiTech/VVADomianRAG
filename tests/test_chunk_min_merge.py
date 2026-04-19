"""STORY F: chunk min-size merging (_merge_small_chunks, _top_section)."""

from __future__ import annotations

from pathlib import Path

import pytest

from ingest import _apply_chunk_min_merge, _merge_small_chunks, _top_section, chunk_markdown_domain


def _m(section: str, idx: int = 0, **extra: str) -> dict:
    d = {
        "section": section,
        "chunk_type": "section",
        "chunk_index": str(idx),
    }
    d.update(extra)
    return d


def test_cm01_merge_three_small_same_top_section():
    sec = "BookTitle > SameHeading"
    chunks = [
        ("x" * 100, _m(sec, 0)),
        ("y" * 80, _m(sec, 1)),
        ("z" * 200, _m(sec, 2)),
    ]
    out = _merge_small_chunks(chunks, min_size=500, max_size=5000)
    assert len(out) == 1
    body, meta = out[0]
    assert len(body) == 100 + 2 + 80 + 2 + 200
    assert "\n\n" in body
    assert meta["chunk_index"] == "0"
    assert meta["section"] == sec


def test_cm02_large_chunk_not_merged_with_small():
    sec = "T > H"
    chunks = [
        ("a" * 600, _m(sec, 0)),
        ("b" * 100, _m(sec, 1)),
        ("c" * 100, _m(sec, 2)),
    ]
    out = _merge_small_chunks(chunks, min_size=500, max_size=5000)
    assert len(out) == 2
    assert len(out[0][0]) == 600
    assert len(out[1][0]) == 100 + 2 + 100
    assert out[0][1]["chunk_index"] == "0"
    assert out[1][1]["chunk_index"] == "1"


def test_cm03_cross_section_not_merged():
    chunks = [
        ("a" * 100, _m("Book > Intro", 0)),
        ("b" * 100, _m("Book > Math", 1)),
    ]
    out = _merge_small_chunks(chunks, min_size=500, max_size=5000)
    assert len(out) == 2


def test_cm04_same_subsection_merge():
    sec = "Book > Intro"
    chunks = [
        ("a" * 100, _m(sec, 0)),
        ("b" * 100, _m(sec, 1)),
    ]
    out = _merge_small_chunks(chunks, min_size=500, max_size=5000)
    assert len(out) == 1
    assert out[0][1]["section"] == sec


def test_cm05_respects_max_size():
    sec = "B > S"
    chunks = [("e" * 200, _m(sec, i)) for i in range(10)]
    out = _merge_small_chunks(chunks, min_size=500, max_size=800)
    assert all(len(t) <= 800 for t, _ in out)
    assert len(out) > 1


def test_cm06_chunk_index_renumbered():
    sec = "B > S"
    chunks = [("a" * 100, _m(sec, i)) for i in range(5)]
    out = _merge_small_chunks(chunks, min_size=500, max_size=5000)
    assert len(out) < 5
    for i, (_, m) in enumerate(out):
        assert m["chunk_index"] == str(i)


def test_cm07_merged_inherits_first_section():
    sec = "Title > A"
    chunks = [
        ("p" * 50, {**_m(sec, 0), "chunk_type": "section"}),
        ("q" * 50, {**_m(sec, 1), "chunk_type": "section"}),
    ]
    out = _merge_small_chunks(chunks, min_size=500, max_size=5000)
    assert len(out) == 1
    assert out[0][1]["section"] == sec
    assert out[0][1]["chunk_type"] == "section"


def test_cm08_empty():
    assert _merge_small_chunks([], min_size=500) == []


def test_cm09_min_size_zero_noop():
    sec = "B > S"
    chunks = [
        ("a" * 50, _m(sec, 0)),
        ("b" * 50, _m(sec, 1)),
        ("c" * 50, _m(sec, 2)),
    ]
    out = _merge_small_chunks(chunks, min_size=0, max_size=5000)
    assert len(out) == 3
    assert out[0][1]["chunk_index"] == "0"
    for i in range(3):
        assert out[i] is chunks[i]


def test_cm10_chunk_markdown_domain_fewer_chunks_with_merge(monkeypatch):
    """Plan: Chapter_04 when present (merge never increases count); synthetic ensures n1 < n0 in CI."""
    model = "nomic-embed-text"
    chapter = (
        Path(__file__).resolve().parents[1]
        / "Studio-Portable-RAG"
        / "DomainDocs"
        / "ngspice"
        / "Chapter_04_Newton_Raphson.md"
    )
    if chapter.is_file():
        text = chapter.read_text(encoding="utf-8", errors="replace")
        monkeypatch.delenv("CHUNK_MIN_SIZE", raising=False)
        monkeypatch.setenv("CHUNK_MIN_SIZE", "0")
        n0 = len(chunk_markdown_domain(text, str(chapter), embed_model=model))
        monkeypatch.setenv("CHUNK_MIN_SIZE", "500")
        n1 = len(chunk_markdown_domain(text, str(chapter), embed_model=model))
        assert n1 <= n0
        if n1 < n0:
            return
    parts = ["# DocTitle\n"]
    for _ in range(25):
        parts.append("## Tiny\n\n" + ("x" * 40) + "\n\n")
    text = "".join(parts)
    path = "synthetic_chapter.md"
    monkeypatch.delenv("CHUNK_MIN_SIZE", raising=False)
    monkeypatch.setenv("CHUNK_MIN_SIZE", "0")
    n0 = len(chunk_markdown_domain(text, path, embed_model=model))
    monkeypatch.setenv("CHUNK_MIN_SIZE", "500")
    n1 = len(chunk_markdown_domain(text, path, embed_model=model))
    assert n0 >= 10
    assert n1 < n0


def test_cm14_chunk_min_size_invalid_env_uses_default(monkeypatch):
    monkeypatch.setenv("CHUNK_MIN_SIZE", "not-an-int")
    sec = "B > S"
    chunks = [("a" * 50, _m(sec, 0)), ("b" * 50, _m(sec, 1))]
    out = _apply_chunk_min_merge(chunks, max_size=5000)
    assert len(out) == 1


def test_cm11_top_section_from_section_number():
    assert _top_section({"section_number": "3.2.1"}) == "3"


def test_cm12_rfc_adjacent_same_top_level_merge():
    chunks = [
        ("a" * 100, {"section_number": "3.1", "section_title": "A", "chunk_strategy": "rfc"}),
        ("b" * 100, {"section_number": "3.2", "section_title": "B", "chunk_strategy": "rfc"}),
    ]
    out = _merge_small_chunks(chunks, min_size=500, max_size=5000)
    assert len(out) == 1
    assert "a" * 100 in out[0][0]


def test_cm13_metadata_preserved_from_first():
    sec = "D > S"
    chunks = [
        (
            "x" * 50,
            {
                **_m(sec, 0),
                "doc_title": "DocOne",
                "source_c_files": "a.c,b.c",
                "device_family": "DIODE",
            },
        ),
        ("y" * 50, {**_m(sec, 1), "doc_title": "Other", "source_c_files": "z.c"}),
    ]
    out = _merge_small_chunks(chunks, min_size=500, max_size=5000)
    assert len(out) == 1
    m = out[0][1]
    assert m["doc_title"] == "DocOne"
    assert m["source_c_files"] == "a.c,b.c"
    assert m["device_family"] == "DIODE"
