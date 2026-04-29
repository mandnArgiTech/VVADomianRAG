"""Interactive REPL for RAG queries."""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Any, Dict

try:
    import readline
except ImportError:  # pragma: no cover
    readline = None  # type: ignore[assignment]

import chromadb
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings

try:
    from rich.console import Console
    from rich.markdown import Markdown

    RICH_AVAILABLE = True
except ImportError:  # pragma: no cover
    Console = None  # type: ignore[misc, assignment]
    Markdown = None  # type: ignore[misc, assignment]
    RICH_AVAILABLE = False

from util.formatting import (
    format_concept_markdown,
    format_json_output,
    format_markdown,
    format_plain,
)

from query_kit.concepts import concept_search_hits
from query_kit.conversation import ConversationMemory, reformulate_query
from query_kit.llm_answer import collect_llm_answer, stream_llm_answer
from query_kit.ollama_client import check_model_available
from query_kit.prompts import effective_system_prompt
from query_kit.search import sync_multi_search_with_dependency_hop
from query_kit.session import SessionState
from query_kit.status_timeout import run_status, run_with_timeout

from query_kit.config import EXIT_OK, HISTORY_FILE

log = logging.getLogger("query")


def make_console(*, no_color: bool, file=None) -> Any:
    if not RICH_AVAILABLE or Console is None:
        return None
    return Console(no_color=no_color, file=file or sys.stdout)


def print_rich(console: Any, text: str, *, use_markdown: bool = True) -> None:
    if console and RICH_AVAILABLE and Markdown is not None and use_markdown:
        console.print(Markdown(text))
    else:
        print(text)


def status_spinner(console: Any, message: str) -> Any:
    if console and RICH_AVAILABLE:
        return console.status(message, spinner="dots")

    class _NoOp:
        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return False

    return _NoOp()


def setup_readline() -> None:
    if readline is None:
        return
    try:
        if HISTORY_FILE.exists():
            readline.read_history_file(str(HISTORY_FILE))
    except OSError:
        pass
    readline.set_history_length(500)


def save_history() -> None:
    if readline is None:
        return
    try:
        readline.write_history_file(str(HISTORY_FILE))
    except OSError:
        pass


def repl_loop(
    cmap: Dict[str, Chroma],
    db_path: str,
    ns: argparse.Namespace,
    chroma_client: chromadb.PersistentClient,
    embedder: OllamaEmbeddings,
) -> int:
    st = SessionState(ns)
    memory = ConversationMemory(st.history_depth)
    setup_readline()
    print("Interactive RAG query. Type /help for commands, Ctrl+D to exit.")
    print(st.show())
    while True:
        try:
            line = input("rag> ").strip()
        except EOFError:
            print()
            save_history()
            return EXIT_OK
        except KeyboardInterrupt:
            print("\n(Interrupted — empty line or /quit to exit)")
            continue
        if not line:
            continue
        if line in ("/quit", "/exit", "exit", "quit"):
            save_history()
            return EXIT_OK
        if line == "/help":
            print(
                "Commands: /set, /show, /help, /status, /history, /clear, /quit\n"
                "  /set <key> <value>\n"
                "Keys: domain, k, type, repo, format, mode, timeout, chat, history_depth\n"
                "Anything else is treated as a search query."
            )
            continue
        if line == "/show":
            print(st.show())
            continue
        if line == "/status":
            print(run_status(db_path))
            continue
        if line == "/history":
            print(memory.show())
            continue
        if line == "/clear":
            memory.clear()
            print("Conversation memory cleared.")
            continue
        if line.startswith("/set "):
            rest = line[5:].strip()
            parts = rest.split(None, 1)
            if len(parts) < 2:
                print("Usage: /set <key> <value>")
                continue
            msg = st.apply_set(parts[0], parts[1])
            print(msg)
            key0 = parts[0].lower().strip()
            if msg.startswith("OK") and key0 in ("history_depth", "history-depth"):
                memory.max_turns = st.history_depth
            continue

        raw_query = line
        search_query = raw_query
        if st.chat and st.mode != "concept" and not memory.is_empty():
            search_query = reformulate_query(raw_query, memory, st.llm_model)
            if search_query != raw_query:
                print(f'(searching for: "{search_query}")')

        rich_ui = RICH_AVAILABLE and st.out_format == "markdown"
        console = make_console(no_color=bool(ns.no_color)) if rich_ui else None

        effective_type = "code" if st.mode == "codebase" else st.search_type
        try:
            with status_spinner(console, "Searching..."):
                if st.mode == "concept":
                    hits = run_with_timeout(
                        st.timeout,
                        concept_search_hits,
                        search_query,
                        st.domain,
                        cmap,
                    )
                else:
                    hits = run_with_timeout(
                        st.timeout,
                        sync_multi_search_with_dependency_hop,
                        search_query,
                        st.top_k,
                        effective_type,
                        st.domain,
                        st.repo,
                        cmap,
                        db_path,
                    )
        except (TimeoutError, ValueError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            continue
        except Exception as exc:
            log.exception("query failed")
            print(f"Error: {exc}", file=sys.stderr)
            continue
        if not hits:
            if st.mode == "concept":
                print(f"No chunks tagged with concept '{search_query}'.")
            else:
                print("No matching chunks found.")
            continue

        hist_msgs = memory.history_messages_for_llm() if st.chat else None
        eff_sp = effective_system_prompt(
            hits, effective_type, st.system_prompt_override, st.domain
        )

        if st.chat:
            llm_tag = check_model_available(st.llm_model)
            if st.mode == "concept":
                if st.out_format == "json":
                    ans = collect_llm_answer(
                        raw_query,
                        hits,
                        llm_tag,
                        eff_sp,
                        hist_msgs,
                    )
                    print(format_json_output(raw_query, hits, "concept", answer=ans))
                elif st.out_format == "markdown":
                    ans = stream_llm_answer(
                        raw_query,
                        hits,
                        llm_tag,
                        eff_sp,
                        console,
                        hist_msgs,
                    )
                else:
                    ans = stream_llm_answer(
                        raw_query,
                        hits,
                        llm_tag,
                        eff_sp,
                        None,
                        hist_msgs,
                    )
                memory.add_turn(raw_query, search_query, ans or "(no answer)")
                continue

            if st.out_format == "json":
                ans = collect_llm_answer(
                    raw_query,
                    hits,
                    llm_tag,
                    eff_sp,
                    hist_msgs,
                )
                print(format_json_output(raw_query, hits, st.mode, answer=ans))
            elif st.out_format == "markdown":
                ans = stream_llm_answer(
                    raw_query,
                    hits,
                    llm_tag,
                    eff_sp,
                    console,
                    hist_msgs,
                )
            else:
                ans = stream_llm_answer(
                    raw_query,
                    hits,
                    llm_tag,
                    eff_sp,
                    None,
                    hist_msgs,
                )
            memory.add_turn(raw_query, search_query, ans or "(no answer)")
            continue

        if st.mode == "concept":
            if st.out_format == "json":
                print(format_json_output(raw_query, hits, "concept"))
            elif st.out_format == "markdown":
                print_rich(console, format_concept_markdown(hits, raw_query))
            else:
                print(format_plain(hits))
        else:
            if st.out_format == "json":
                print(format_json_output(raw_query, hits, st.mode))
            elif st.out_format == "markdown":
                print_rich(console, format_markdown(hits, raw_query))
            else:
                print(format_plain(hits))
    return EXIT_OK


_make_console = make_console
_print_rich = print_rich
_status_spinner = status_spinner
_setup_readline = setup_readline
_save_history = save_history
