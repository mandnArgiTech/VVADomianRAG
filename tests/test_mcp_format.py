"""Tests for mcp_server format_result, context_window, and _truncate_chunk."""
from __future__ import annotations

from langchain_core.documents import Document

import mcp_server as mcp
import util.formatting as util_formatting


def test_format_result_prefers_context_window():
    doc = Document(
        page_content="tiny",
        metadata={
            "repository": "r",
            "relative_path": "a.c",
            "extension": ".c",
            "chunk_name": "f",
            "context_window": "EXPANDED_WINDOW_BODY",
        },
    )
    out = mcp.format_result(doc, 0.1, "code")
    assert "EXPANDED_WINDOW_BODY" in out
    assert "tiny" not in out


def test_truncate_chunk_respects_custom_limit(monkeypatch):
    monkeypatch.setattr(util_formatting, "RESULT_CHUNK_MAX_CHARS", 100)
    body = "a\n\n" + "x" * 200
    out = mcp._truncate_chunk(body, max_chars=100)
    assert "\n\n... (truncated) ..." in out
    assert out.startswith("a\n\n")


def test_truncate_chunk_closing_brace_boundary():
    # `}` at index 1000 so with max_chars=2000 (floor 1000) the brace anchor is valid
    body = "y" * 1000 + "}" + "y" * 800
    out = mcp._truncate_chunk(body, max_chars=1500)
    marker = "\n\n... (truncated) ..."
    assert marker in out
    idx = out.index(marker)
    assert idx > 0 and out[idx - 1] == "}"


def test_truncate_chunk_closes_odd_inner_fence(monkeypatch):
    monkeypatch.setattr(util_formatting, "RESULT_CHUNK_MAX_CHARS", 100)
    text = "```c\nint x;\n" + "z" * 120
    out = mcp._truncate_chunk(text, max_chars=100)
    assert "\n\n... (truncated) ..." in out
    assert out.count("```") % 2 == 0


def test_format_result_code_calls_uses_iter_concept_ids_style():
    doc = Document(
        page_content="body",
        metadata={
            "repository": "r",
            "relative_path": "a.c",
            "extension": ".c",
            "chunk_name": "f",
            "calls": "foo, bar",
        },
    )
    out = mcp.format_result(doc, None, "code")
    assert "Callees" in out
    assert "foo" in out and "bar" in out


def test_context_window_uses_larger_cap(monkeypatch):
    monkeypatch.setattr(util_formatting, "RESULT_CHUNK_MAX_CHARS", 50)
    monkeypatch.setattr(util_formatting, "RESULT_CONTEXT_WINDOW_MAX_CHARS", 120)
    long_cw = "W" * 80
    doc = Document(
        page_content="x",
        metadata={
            "repository": "r",
            "relative_path": "a.c",
            "extension": ".c",
            "chunk_name": "f",
            "context_window": long_cw,
        },
    )
    out = mcp.format_result(doc, None, "code")
    assert long_cw in out
    assert "truncated" not in out
