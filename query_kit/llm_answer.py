"""Non-streaming and streaming Ollama chat over retrieved context."""

from __future__ import annotations

import sys
from typing import Any, Dict, List, Optional

try:
    from rich.live import Live
    from rich.markdown import Markdown

    _RICH_LIVE = True
except ImportError:  # pragma: no cover
    Live = None  # type: ignore[misc, assignment]
    Markdown = None  # type: ignore[misc, assignment]
    _RICH_LIVE = False

from util.search_primitives import SearchHit

from query_kit.context import build_context_blocks
from query_kit.ollama_client import (
    OLLAMA_LIB_AVAILABLE,
    _ollama_mod,
    ollama_chat,
    ollama_options_for_model,
    stream_chunk_text,
)


def collect_llm_answer(
    user_query: str,
    hits: List[SearchHit],
    llm_model: str,
    system_prompt: str,
    history_messages: Optional[List[Dict[str, str]]] = None,
) -> str:
    if not OLLAMA_LIB_AVAILABLE or _ollama_mod is None:
        print("Warning: ollama package not installed; skipping LLM answer.", file=sys.stderr)
        return ""
    context = build_context_blocks(hits)
    messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
    if history_messages:
        messages.extend(history_messages)
    messages.append(
        {
            "role": "user",
            "content": f"Context:\n\n{context}\n\n---\n\nQuestion: {user_query}",
        }
    )
    try:
        resp = ollama_chat(
            model=llm_model,
            messages=messages,
            stream=False,
            options=ollama_options_for_model(llm_model),
        )
        msg = getattr(resp, "message", None) or (resp.get("message") if isinstance(resp, dict) else None)
        if isinstance(msg, dict):
            return str(msg.get("content") or "")
        return str(getattr(msg, "content", None) or "")
    except Exception as exc:
        err = str(exc).lower()
        if "not found" in err or "pull" in err:
            print(
                f"Error: model {llm_model!r} not found. Run: ollama pull {llm_model}",
                file=sys.stderr,
            )
        else:
            print(f"Error: LLM call failed: {exc}", file=sys.stderr)
        return ""


def stream_llm_answer(
    user_query: str,
    hits: List[SearchHit],
    llm_model: str,
    system_prompt: str,
    console: Any,
    history_messages: Optional[List[Dict[str, str]]] = None,
) -> str:
    if not OLLAMA_LIB_AVAILABLE or _ollama_mod is None:
        print("Warning: ollama package not installed; skipping LLM answer.", file=sys.stderr)
        return ""
    context = build_context_blocks(hits)
    messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
    if history_messages:
        messages.extend(history_messages)
    messages.append(
        {
            "role": "user",
            "content": f"Context:\n\n{context}\n\n---\n\nQuestion: {user_query}",
        }
    )
    try:
        stream = ollama_chat(
            model=llm_model,
            messages=messages,
            stream=True,
            options=ollama_options_for_model(llm_model),
        )
    except Exception as exc:
        err = str(exc).lower()
        if "not found" in err or "pull" in err:
            print(
                f"Error: model {llm_model!r} not found. Run: ollama pull {llm_model}",
                file=sys.stderr,
            )
        else:
            print(f"Error: LLM call failed: {exc}", file=sys.stderr)
        return ""

    parts: List[str] = []
    try:
        if console is not None and _RICH_LIVE and Live is not None and Markdown is not None:
            with Live(Markdown(""), console=console, refresh_per_second=12, transient=False) as live:
                for chunk in stream:
                    tok = stream_chunk_text(chunk)
                    if tok:
                        parts.append(tok)
                        live.update(Markdown("".join(parts)))
        else:
            for chunk in stream:
                tok = stream_chunk_text(chunk)
                if tok:
                    parts.append(tok)
                    print(tok, end="", flush=True)
            if parts:
                print()
    except KeyboardInterrupt:
        print("\n(generation interrupted)", file=sys.stderr)
    return "".join(parts)


_collect_llm_answer = collect_llm_answer
_stream_llm_answer = stream_llm_answer
