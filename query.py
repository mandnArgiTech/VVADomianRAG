#!/usr/bin/env python3
"""
query.py — Terminal AI agent: hybrid RAG search (BM25 + dense + RRF), optional LLM chat,
stateful REPL, and rich terminal output. Standalone; does not import mcp_server.

Implementation lives in ``query_kit/`` for reuse; this module re-exports the historical ``query.*``
API for tests, GUI, and MCP.
"""
from __future__ import annotations

import logging
import urllib.request

from util.chunk_metadata import parse_dependency_tokens as _parse_dependency_tokens
from util.chroma_client import (
    detect_embedding_model,
    embedding_model_from_db_path,
    persistent_chroma_client as _persistent_chroma_client,
)
from util.constants import (
    GOD_MODE_MIN_CONTENT_SIZE,
    HYBRID_SEARCH,
    MAX_K,
    QUERY_CALLER_MAX_HITS,
    QUERY_DEP_LOOKUP_K,
    QUERY_DEP_MAX_HITS,
    QUERY_DEP_MAX_TOKENS,
    RESULT_CHUNK_MAX_CHARS,
    RESULT_CONTEXT_WINDOW_MAX_CHARS,
    RRF_K,
    TOP_K_DEFAULT,
)
from util.formatting import (
    fence_for as _fence_for,
    format_concept_markdown,
    format_json_output,
    format_markdown,
    format_plain,
    format_result,
    infer_source_type as _infer_source_type,
    truncate_chunk as _truncate_chunk,
)
from util.search_primitives import SearchHit, domain_filter as _domain_filter

from query_kit.chroma_session import connect_chroma_with_retry
from query_kit.cli import main, parse_args
from query_kit.config import (
    CHAT_MODEL_FALLBACKS,
    DEFAULT_CHAT_LLM,
    DEFAULT_TIMEOUT,
    EXIT_ARG,
    EXIT_INFRA,
    EXIT_NO_RESULTS,
    EXIT_OK,
    HISTORY_FILE,
    QUERY_PROMPT_DOC_THRESHOLD,
    QUERY_PROMPT_TOP_M,
    RAG_CONTEXT_MAX_CHARS,
)
from query_kit.context import build_context_blocks as _build_context_blocks
from query_kit.concepts import concept_search_hits
from query_kit.concepts import concept_parts as _concept_parts
from query_kit.conversation import ConversationMemory, reformulate_query
from query_kit.god_mode import (
    _expand_query_typos,
    _god_mode_chunk_name_matches,
    _load_symbols_vocab,
    _vocab_cache,
)
from query_kit.llm_answer import _collect_llm_answer, _stream_llm_answer
from query_kit.ollama_client import (
    OLLAMA_LIB_AVAILABLE,
    _check_model_available,
    _ollama_mod,
    _ollama_options_for_model,
    _stream_chunk_text,
    check_ollama,
    default_chat_llm_from_env,
    estimate_tokens,
)
from query_kit.prompt_strings import (
    DEBUG_SYSTEM_PROMPT as _DEBUG_SYSTEM_PROMPT,
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_SYSTEM_PROMPTS,
    GENERIC_SYSTEM_PROMPT as _GENERIC_SYSTEM_PROMPT,
    NGSPICE_SYSTEM_PROMPT as _NGSPICE_SYSTEM_PROMPT,
)
from query_kit.prompts import _effective_system_prompt, _load_system_prompt
from query_kit.repl import (
    _make_console,
    _print_rich,
    _save_history,
    _setup_readline,
    _status_spinner,
    repl_loop,
)
from query_kit.search import (
    _exact_chunk_name_hits,
    _fused_docs_for_query_text,
    _resolve_db_abs,
    _sync_fetch_callers,
    _sync_fetch_dependents,
    _sync_multi_search,
    _sync_multi_search_with_dependency_hop,
)
from query_kit.session import SessionState
from query_kit.status_timeout import run_status, run_with_timeout

log = logging.getLogger("query")

__all__ = [
    "CHAT_MODEL_FALLBACKS",
    "ConversationMemory",
    "DEFAULT_CHAT_LLM",
    "DEFAULT_SYSTEM_PROMPT",
    "DEFAULT_SYSTEM_PROMPTS",
    "DEFAULT_TIMEOUT",
    "EXIT_ARG",
    "EXIT_INFRA",
    "EXIT_NO_RESULTS",
    "EXIT_OK",
    "GOD_MODE_MIN_CONTENT_SIZE",
    "HYBRID_SEARCH",
    "HISTORY_FILE",
    "MAX_K",
    "OLLAMA_LIB_AVAILABLE",
    "QUERY_CALLER_MAX_HITS",
    "QUERY_DEP_LOOKUP_K",
    "QUERY_DEP_MAX_HITS",
    "QUERY_DEP_MAX_TOKENS",
    "QUERY_PROMPT_DOC_THRESHOLD",
    "QUERY_PROMPT_TOP_M",
    "RAG_CONTEXT_MAX_CHARS",
    "RESULT_CHUNK_MAX_CHARS",
    "RESULT_CONTEXT_WINDOW_MAX_CHARS",
    "RRF_K",
    "SearchHit",
    "SessionState",
    "TOP_K_DEFAULT",
    "_DEBUG_SYSTEM_PROMPT",
    "_GENERIC_SYSTEM_PROMPT",
    "_NGSPICE_SYSTEM_PROMPT",
    "_collect_llm_answer",
    "_concept_parts",
    "_domain_filter",
    "_effective_system_prompt",
    "_exact_chunk_name_hits",
    "_expand_query_typos",
    "_fence_for",
    "_fused_docs_for_query_text",
    "_god_mode_chunk_name_matches",
    "_infer_source_type",
    "_load_symbols_vocab",
    "_load_system_prompt",
    "_make_console",
    "_ollama_mod",
    "_ollama_options_for_model",
    "_parse_dependency_tokens",
    "_print_rich",
    "_resolve_db_abs",
    "_save_history",
    "_setup_readline",
    "_status_spinner",
    "_stream_chunk_text",
    "_stream_llm_answer",
    "_sync_fetch_callers",
    "_sync_fetch_dependents",
    "_sync_multi_search",
    "_sync_multi_search_with_dependency_hop",
    "_truncate_chunk",
    "_vocab_cache",
    "check_ollama",
    "concept_search_hits",
    "connect_chroma_with_retry",
    "default_chat_llm_from_env",
    "detect_embedding_model",
    "embedding_model_from_db_path",
    "estimate_tokens",
    "format_concept_markdown",
    "format_json_output",
    "format_markdown",
    "format_plain",
    "format_result",
    "main",
    "parse_args",
    "reformulate_query",
    "repl_loop",
    "run_status",
    "run_with_timeout",
]
