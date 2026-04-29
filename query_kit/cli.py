"""Argument parsing and ``main`` entry for the terminal RAG client."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import List, Optional

from util.chroma_client import detect_embedding_model
from util.constants import MAX_K, TOP_K_DEFAULT
from util.formatting import (
    format_concept_markdown,
    format_json_output,
    format_markdown,
    format_plain,
)

from query_kit.chroma_session import connect_chroma_with_retry
from query_kit.config import DEFAULT_TIMEOUT, EXIT_ARG, EXIT_INFRA, EXIT_NO_RESULTS, EXIT_OK
from query_kit.concepts import concept_search_hits
from query_kit.llm_answer import collect_llm_answer, stream_llm_answer
from query_kit.ollama_client import check_model_available, check_ollama, default_chat_llm_from_env
from query_kit.prompts import effective_system_prompt
from query_kit.repl import RICH_AVAILABLE, make_console, print_rich, repl_loop, status_spinner
from query_kit.search import sync_multi_search_with_dependency_hop
from query_kit.status_timeout import run_status, run_with_timeout

_REPO_ROOT = Path(__file__).resolve().parent.parent


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Query Universal Domain RAG (Chroma + Ollama).")
    p.add_argument("-q", "--query", default="", help="Search text (concept id in concept mode)")
    p.add_argument(
        "-m",
        "--mode",
        choices=("semantic", "concept", "codebase", "status"),
        default="semantic",
        help="Search mode (default: semantic)",
    )
    p.add_argument(
        "-t",
        "--search-type",
        choices=("auto", "code", "domain", "troubleshoot", "reference"),
        default="auto",
        help="Collection routing for semantic/codebase (default: auto)",
    )
    p.add_argument("-d", "--domain", default="", help="Filter collections by name substring")
    p.add_argument("-r", "--repo", default="", help="Filter by repository metadata")
    p.add_argument("-k", "--top-k", type=int, default=TOP_K_DEFAULT, help=f"Max results (1–{MAX_K})")
    p.add_argument(
        "-f",
        "--format",
        dest="format",
        choices=("markdown", "json", "plain"),
        default="markdown",
        help="Output format",
    )
    p.add_argument("-o", "--output", default="", help="Write output to file instead of stdout")
    p.add_argument(
        "-c",
        "--chat",
        action="store_true",
        help="After retrieval, generate an answer with the LLM (Ollama chat)",
    )
    p.add_argument(
        "--llm-model",
        default="",
        help="Ollama chat model for --chat (default: gemma3:27b; env RAG_LLM_MODEL overrides when flag omitted)",
    )
    p.add_argument(
        "--system-prompt",
        default="",
        help="Override default RAG system prompt when using --chat",
    )
    p.add_argument(
        "--history-depth",
        type=int,
        default=5,
        help="REPL: max conversation turns to remember with --chat (default: 5)",
    )
    p.add_argument("--no-color", action="store_true", help="Disable color (rich/ANSI)")
    p.add_argument(
        "--db-path",
        default=os.environ.get("DB_PATH", "").strip()
        or str(_REPO_ROOT / "Studio-Portable-RAG" / "VectorDB"),
        help="Chroma persist directory",
    )
    p.add_argument("--model", default="", help="Embedding model (default: auto-detect)")
    p.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Per-query timeout (seconds)")
    p.add_argument("-i", "--interactive", action="store_true", help="Interactive REPL")
    p.add_argument("-v", "--verbose", action="store_true", help="Verbose logging on stderr")
    p.add_argument("--quiet", action="store_true", help="Suppress banners")
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    ns = parse_args(argv)
    log = logging.getLogger("query")
    logging.basicConfig(
        level=logging.DEBUG if ns.verbose else logging.WARNING,
        format="%(levelname)s %(message)s",
        stream=sys.stderr,
    )

    db_path = str(Path(ns.db_path).resolve())
    if not Path(db_path).is_dir():
        if not ns.quiet:
            print(f"Error: DB path is not a directory: {db_path}", file=sys.stderr)
        return EXIT_INFRA

    need_query = not ns.interactive and ns.mode != "status"
    if need_query and not (ns.query or "").strip():
        if not ns.quiet:
            print("Error: --query is required unless --interactive or --mode status", file=sys.stderr)
        return EXIT_ARG

    if ns.mode == "status":
        text = run_status(db_path)
        if ns.output:
            Path(ns.output).write_text(text, encoding="utf-8")
        else:
            print(text)
        return EXIT_OK

    if not check_ollama():
        if not ns.quiet:
            print(
                "Error: Ollama not reachable at http://127.0.0.1:11434/api/tags. "
                "Start Ollama or use query.sh.",
                file=sys.stderr,
            )
        return EXIT_INFRA

    model = ns.model.strip() or detect_embedding_model(db_path)
    if not ns.quiet:
        print(f"DB: {db_path}\nModel: {model}", file=sys.stderr)

    try:
        chroma_client, embedder, cmap = connect_chroma_with_retry(db_path, model)
    except Exception as exc:
        if not ns.quiet:
            print(f"Error: {exc}", file=sys.stderr)
        return EXIT_INFRA

    if not cmap:
        if not ns.quiet:
            print("Error: no Chroma collections in DB.", file=sys.stderr)
        return EXIT_INFRA

    if ns.interactive:
        return repl_loop(cmap, db_path, ns, chroma_client, embedder)

    effective_type = "code" if ns.mode == "codebase" else ns.search_type
    try:
        k = max(1, min(int(ns.top_k), MAX_K))
    except (TypeError, ValueError):
        k = TOP_K_DEFAULT

    q = ns.query.strip()
    spin_console = make_console(no_color=bool(ns.no_color)) if (RICH_AVAILABLE and ns.format == "markdown") else None
    display_console = make_console(no_color=bool(ns.no_color)) if (
        RICH_AVAILABLE and ns.format == "markdown" and not ns.output
    ) else None

    try:
        with status_spinner(spin_console, "Searching..."):
            if ns.mode == "concept":
                hits = run_with_timeout(
                    int(ns.timeout),
                    concept_search_hits,
                    q,
                    ns.domain,
                    cmap,
                )
            else:
                hits = run_with_timeout(
                    int(ns.timeout),
                    sync_multi_search_with_dependency_hop,
                    q,
                    k,
                    effective_type,
                    ns.domain,
                    ns.repo,
                    cmap,
                    db_path,
                )
    except TimeoutError as exc:
        if not ns.quiet:
            print(f"Error: {exc}", file=sys.stderr)
        return EXIT_INFRA
    except Exception as exc:
        log.exception("search failed")
        if not ns.quiet:
            print(f"Error: {exc}", file=sys.stderr)
        return EXIT_INFRA

    if not hits:
        msg = "No matching chunks found."
        if ns.output:
            Path(ns.output).write_text(msg + "\n", encoding="utf-8")
        elif not ns.quiet:
            print(msg)
        return EXIT_NO_RESULTS

    llm_model = (ns.llm_model or "").strip() or default_chat_llm_from_env()
    sp_override = (ns.system_prompt or "").strip() or None
    system_prompt = effective_system_prompt(hits, effective_type, sp_override, ns.domain)

    if ns.chat:
        llm_tag = check_model_available(llm_model)
        if ns.mode == "concept":
            mode_label = "concept"
        else:
            mode_label = ns.mode
        if ns.format == "json":
            ans = collect_llm_answer(q, hits, llm_tag, system_prompt, None)
            text = format_json_output(q, hits, mode_label, answer=ans)
            if ns.output:
                Path(ns.output).write_text(text, encoding="utf-8")
            else:
                print(text)
            return EXIT_OK
        if ns.format == "plain":
            if ns.output:
                ans = collect_llm_answer(q, hits, llm_tag, system_prompt, None)
                Path(ns.output).write_text(ans + ("\n" if ans and not ans.endswith("\n") else ""), encoding="utf-8")
            else:
                stream_llm_answer(q, hits, llm_tag, system_prompt, None, None)
            return EXIT_OK
        if ns.output:
            ans = collect_llm_answer(q, hits, llm_tag, system_prompt, None)
            Path(ns.output).write_text(ans + ("\n" if ans and not ans.endswith("\n") else ""), encoding="utf-8")
        else:
            stream_llm_answer(q, hits, llm_tag, system_prompt, display_console, None)
        return EXIT_OK

    if ns.mode == "concept":
        text = (
            format_json_output(q, hits, "concept")
            if ns.format == "json"
            else format_concept_markdown(hits, q)
            if ns.format == "markdown"
            else format_plain(hits)
        )
    else:
        text = (
            format_json_output(q, hits, ns.mode)
            if ns.format == "json"
            else format_markdown(hits, q)
            if ns.format == "markdown"
            else format_plain(hits)
        )

    if ns.output:
        Path(ns.output).write_text(text, encoding="utf-8")
    elif ns.format == "markdown" and display_console:
        print_rich(display_console, text)
    else:
        print(text)
    return EXIT_OK

