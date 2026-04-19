"""Story H: ingest tiny-chunk filter, gitignore entries, God mode size + stem denylist (IQ-01–IQ-12)."""

from __future__ import annotations

import os
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

from ingest import _NGSPICE_GITIGNORE_ENTRIES, _filter_tiny_code_chunks
from query import _exact_chunk_name_hits, _god_mode_chunk_name_matches


def _chunk(text: str, ctype: str, idx: str = "0") -> tuple[str, Dict[str, str]]:
    return (text, {"chunk_type": ctype, "chunk_index": idx, "chunk_name": "n"})


def test_iq01_code_chunks_under_50_chars_dropped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODE_CHUNK_MIN_SIZE", "50")
    chunks = [_chunk("a" * 20, "declaration"), _chunk("b" * 60, "declaration"), _chunk("c" * 200, "declaration")]
    out = _filter_tiny_code_chunks(chunks)
    # Short declarations are also dropped unless >=200 chars (noise reduction).
    assert [len(x[0]) for x in out] == [200]


def test_iq02_file_preamble_short_preserved(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODE_CHUNK_MIN_SIZE", "50")
    chunks = [_chunk("short", "file_preamble")]
    out = _filter_tiny_code_chunks(chunks)
    assert len(out) == 1 and out[0][0] == "short"


def test_iq03_code_chunk_min_size_zero_disables(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODE_CHUNK_MIN_SIZE", "0")
    chunks = [_chunk("tiny", "declaration"), _chunk("x" * 100, "declaration")]
    out = _filter_tiny_code_chunks(chunks)
    assert len(out) == 2


def test_iq04_code_chunk_min_size_100_filters_60(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODE_CHUNK_MIN_SIZE", "100")
    chunks = [_chunk("b" * 60, "declaration"), _chunk("c" * 200, "declaration")]
    out = _filter_tiny_code_chunks(chunks)
    assert [len(x[0]) for x in out] == [200]


def test_iq05_gitignore_has_adms_and_ciderlib() -> None:
    assert "src/spicelib/devices/adms/" in _NGSPICE_GITIGNORE_ENTRIES
    assert "src/ciderlib/" in _NGSPICE_GITIGNORE_ENTRIES


def test_iq06_god_mode_exact_hits_skip_tiny_content(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CODE_CHUNK_MIN_SIZE", raising=False)

    class _FakeCol:
        def get(self, **_kwargs: Any) -> Dict[str, List[Any]]:
            return {
                "documents": ["x" * 10, "y" * 60, "z" * 200],
                "metadatas": [{"chunk_name": "foo"}, {"chunk_name": "foo"}, {"chunk_name": "foo"}],
                "ids": ["1", "2", "3"],
            }

    vs = MagicMock()
    vs._collection = _FakeCol()
    cmap = {"spice_code": vs}
    vocab = frozenset({"foo"})
    hits = _exact_chunk_name_hits("foo bar", ["spice_code"], cmap, "", vocab)
    assert len(hits) == 2
    assert {len(h.content) for h in hits} == {60, 200}


def test_iq07_god_mode_denylist_blocks_terminal() -> None:
    vocab = frozenset({"terminal", "voltage"})
    m = _god_mode_chunk_name_matches("thermal voltage terminal", vocab)
    assert "terminal" not in m


def test_iq08_god_mode_denylist_does_not_block_dioload() -> None:
    vocab = frozenset({"DIOload", "thermal"})
    m = _god_mode_chunk_name_matches("DIOload thermal", vocab)
    assert "DIOload" in m


def test_iq09_god_mode_denylist_allows_terminal_when_filename_in_query() -> None:
    # ``terminal.c`` is a single ``[\w\.]+`` token, so include a separate ``terminal`` token
    # while the query still names the file (AC-4).
    vocab = frozenset({"terminal"})
    m = _god_mode_chunk_name_matches("open terminal.c for terminal debug", vocab)
    assert "terminal" in m


def test_iq10_god_mode_denylist_case_insensitive() -> None:
    vocab = frozenset({"terminal"})
    m = _god_mode_chunk_name_matches("Thermal Voltage Terminal", vocab)
    assert "terminal" not in m


def test_iq11_chunk_index_sequential_after_filter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODE_CHUNK_MIN_SIZE", "50")
    chunks = [
        _chunk("a" * 40, "declaration", "0"),
        _chunk("b" * 250, "declaration", "1"),
        _chunk("c" * 30, "declaration", "2"),
        _chunk("d" * 70, "function_definition", "3"),
        _chunk("e" * 20, "declaration", "4"),
    ]
    out = _filter_tiny_code_chunks(chunks)
    # Large declaration + short function (declaration <200 dropped including 60-char case).
    assert [m["chunk_index"] for _, m in out] == ["0", "1"]
    assert [len(c[0]) for c in out] == [250, 70]


def test_iq12_core_constant_short_preserved(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODE_CHUNK_MIN_SIZE", "50")
    chunks = [_chunk("#define X 1", "core_constant")]
    out = _filter_tiny_code_chunks(chunks)
    assert len(out) == 1 and out[0][1]["chunk_type"] == "core_constant"


def test_declaration_under_200_chars_dropped_even_above_code_min(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CODE_CHUNK_MIN_SIZE", "50")
    chunks = [
        _chunk("x" * 199, "declaration"),
        _chunk("y" * 200, "declaration"),
    ]
    out = _filter_tiny_code_chunks(chunks)
    assert len(out) == 1 and len(out[0][0]) == 200
