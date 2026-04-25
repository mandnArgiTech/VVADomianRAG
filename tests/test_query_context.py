"""Unit tests for query.py context building, truncation, dependency tokens, and system prompt routing."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import query as q
import util.formatting as util_formatting


def test_parse_dependency_tokens_order_and_dedupe():
    assert q._parse_dependency_tokens("a.h, b.h, a.h") == ["a.h", "b.h"]
    assert q._parse_dependency_tokens("") == []


def test_expand_query_typos_typo_filename(tmp_path, monkeypatch):
    monkeypatch.setattr(q, "_vocab_cache", {})
    vocab_file = Path(tmp_path) / "symbols_vocabulary.json"
    vocab_file.write_text(json.dumps(["niiter.c", "foo.h"]), encoding="utf-8")
    vocab = q._load_symbols_vocab(str(tmp_path))
    out = q._expand_query_typos("where is niniter.c defined", vocab)
    assert "[Auto-expanded:" in out
    assert "niiter.c" in out


def test_expand_query_typos_unchanged_when_in_vocab():
    vocab = frozenset({"niiter.c"})
    assert q._expand_query_typos("niiter.c", vocab) == "niiter.c"


def test_expand_query_typos_empty_vocab():
    assert q._expand_query_typos("any niniter.c", frozenset()) == "any niniter.c"


def test_god_mode_chunk_name_matches_sentence_case_insensitive():
    vocab = frozenset({"DCtrCurv", "niiter.c"})
    names = q._god_mode_chunk_name_matches("where is dctrcurv defined like niiter.c", vocab)
    assert "DCtrCurv" in names
    assert "niiter.c" in names


def test_god_mode_chunk_name_matches_empty_vocab():
    assert q._god_mode_chunk_name_matches("any DCtrCurv", frozenset()) == []


def test_god_mode_single_token_falls_back_when_not_in_vocab():
    vocab = frozenset({"Other"})
    assert q._god_mode_chunk_name_matches("NotInVocabAtAll", vocab) == ["NotInVocabAtAll"]


def test_truncate_chunk_short_unchanged():
    assert q._truncate_chunk("hello") == "hello"


def test_truncate_chunk_prefers_newline_boundary(monkeypatch):
    monkeypatch.setattr(util_formatting, "RESULT_CHUNK_MAX_CHARS", 100)
    body = "line0\n" + "x" * 200 + "\nline2"
    out = q._truncate_chunk(body)
    assert "truncated" in out
    assert out.count("```") % 2 == 0
    assert out.startswith("line0\n")


def test_truncate_chunk_closes_odd_fence(monkeypatch):
    monkeypatch.setattr(util_formatting, "RESULT_CHUNK_MAX_CHARS", 80)
    text = "```c\nint x = 1;\n" + "y" * 100
    out = q._truncate_chunk(text)
    assert out.rstrip().endswith("```") or "```" in out


def test_effective_system_prompt_override():
    hits = [
        q.SearchHit("a", None, "rally", {}, "c"),
    ]
    assert q._effective_system_prompt(hits, "auto", "CUSTOM") == "CUSTOM"


def test_effective_system_prompt_doc_majority_generic():
    hits = [
        q.SearchHit("a", None, "rally", {}, "c"),
        q.SearchHit("b", None, "customer", {}, "c"),
        q.SearchHit("c", None, "community", {}, "c"),
        q.SearchHit("d", None, "code", {}, "c"),
        q.SearchHit("e", None, "code", {}, "c"),
    ]
    sp = q._effective_system_prompt(hits, "auto", None)
    assert sp == q._GENERIC_SYSTEM_PROMPT


def test_effective_system_prompt_doc_majority_debug_troubleshoot():
    hits = [
        q.SearchHit("a", None, "rally", {}, "c"),
        q.SearchHit("b", None, "customer", {}, "c"),
        q.SearchHit("c", None, "community", {}, "c"),
        q.SearchHit("d", None, "code", {}, "c"),
        q.SearchHit("e", None, "code", {}, "c"),
    ]
    sp = q._effective_system_prompt(hits, "troubleshoot", None)
    assert sp == q._DEBUG_SYSTEM_PROMPT


def test_effective_system_prompt_code_majority_generic():
    hits = [
        q.SearchHit("a", None, "code", {}, "c"),
        q.SearchHit("b", None, "code", {}, "c"),
        q.SearchHit("c", None, "code", {}, "c"),
        q.SearchHit("d", None, "rally", {}, "c"),
    ]
    sp = q._effective_system_prompt(hits, "auto", None)
    assert sp == q._GENERIC_SYSTEM_PROMPT


def test_build_context_blocks_prefers_context_window():
    hits = [
        q.SearchHit(
            "small",
            None,
            "code",
            {"relative_path": "f.c", "context_window": "WIDE " * 20, "chunk_name": "fn"},
            "col",
        )
    ]
    ctx = q._build_context_blocks(hits, max_chars=50000)
    assert "WIDE" in ctx
    assert "Source 1" in ctx


def test_format_result_prefers_context_window_for_markdown(monkeypatch):
    """Agent tool path uses format_markdown → format_result; body must come from context_window."""
    monkeypatch.setattr(util_formatting, "RESULT_CHUNK_MAX_CHARS", 40)
    monkeypatch.setattr(util_formatting, "RESULT_CONTEXT_WINDOW_MAX_CHARS", 500)
    marker = "UNIQUE_CONTEXT_WINDOW_BODY_MARKER"
    meta = {
        "relative_path": "f.c",
        "chunk_name": "foo",
        "chunk_type": "function",
        "extension": ".c",
        "context_window": "preamble\n" + marker + "\n" + ("x" * 80),
    }
    doc = type("D", (), {"page_content": "tiny", "metadata": meta})()
    out = q.format_result(doc, 0.1, "code")
    assert marker in out
    assert "### Code" in out


@patch.object(q, "_sync_multi_search", return_value=[])
def test_dependency_hop_delegates_to_primary_when_disabled(mock_sync, monkeypatch):
    monkeypatch.setenv("QUERY_DEP_MAX_HITS", "0")
    monkeypatch.setattr(q, "QUERY_DEP_MAX_HITS", 0)
    monkeypatch.setattr(q, "QUERY_DEP_MAX_TOKENS", 16)
    cmap = {}
    out = q._sync_multi_search_with_dependency_hop("q", 5, "code", "", "", cmap, "")
    assert out == []
    mock_sync.assert_called_once()
