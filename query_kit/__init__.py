"""Reusable RAG query building blocks: hybrid search, god-mode prefetch, Ollama chat, REPL.

Domain-specific defaults live under ``system_prompts/`` at the repository root when using this
package from VVADomianRAG; pass ``prompts_dir`` to :func:`query_kit.prompts.load_system_prompt` for
other projects.

Typical reuse::

    from query_kit.chroma_session import connect_chroma_with_retry
    from query_kit.search import sync_multi_search_with_dependency_hop
    from util.chroma_client import detect_embedding_model

See ``query.py`` at repo root for the full CLI (thin wrapper).
"""

from __future__ import annotations

from query_kit.chroma_session import connect_chroma_with_retry
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
from query_kit.concepts import concept_parts, concept_search_hits
from query_kit.context import build_context_blocks
from query_kit.conversation import ConversationMemory, reformulate_query
from query_kit.god_mode import (
    expand_query_typos,
    god_mode_chunk_name_matches,
    is_noise_stem,
    load_symbols_vocab,
)
from query_kit.ollama_client import (
    OLLAMA_LIB_AVAILABLE,
    check_model_available,
    check_ollama,
    default_chat_llm_from_env,
    estimate_tokens,
    ollama_chat_model_names,
    ollama_options_for_model,
    stream_chunk_text,
)
from query_kit.prompt_strings import (
    DEBUG_SYSTEM_PROMPT,
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_SYSTEM_PROMPTS,
    GENERIC_SYSTEM_PROMPT,
    NGSPICE_SYSTEM_PROMPT,
)
from query_kit.prompts import effective_system_prompt, load_system_prompt
from query_kit.search import (
    exact_chunk_name_hits,
    sync_fetch_callers,
    sync_fetch_dependents,
    sync_multi_search,
    sync_multi_search_with_dependency_hop,
)
from query_kit.session import SessionState
from query_kit.status_timeout import run_status, run_with_timeout

__all__ = [
    "CHAT_MODEL_FALLBACKS",
    "ConversationMemory",
    "DEBUG_SYSTEM_PROMPT",
    "DEFAULT_CHAT_LLM",
    "DEFAULT_SYSTEM_PROMPT",
    "DEFAULT_SYSTEM_PROMPTS",
    "DEFAULT_TIMEOUT",
    "EXIT_ARG",
    "EXIT_INFRA",
    "EXIT_NO_RESULTS",
    "EXIT_OK",
    "GENERIC_SYSTEM_PROMPT",
    "HISTORY_FILE",
    "NGSPICE_SYSTEM_PROMPT",
    "OLLAMA_LIB_AVAILABLE",
    "QUERY_PROMPT_DOC_THRESHOLD",
    "QUERY_PROMPT_TOP_M",
    "RAG_CONTEXT_MAX_CHARS",
    "SessionState",
    "build_context_blocks",
    "check_model_available",
    "check_ollama",
    "concept_parts",
    "concept_search_hits",
    "connect_chroma_with_retry",
    "default_chat_llm_from_env",
    "estimate_tokens",
    "effective_system_prompt",
    "exact_chunk_name_hits",
    "expand_query_typos",
    "god_mode_chunk_name_matches",
    "is_noise_stem",
    "load_symbols_vocab",
    "load_system_prompt",
    "ollama_chat_model_names",
    "ollama_options_for_model",
    "reformulate_query",
    "run_status",
    "run_with_timeout",
    "stream_chunk_text",
    "sync_fetch_callers",
    "sync_fetch_dependents",
    "sync_multi_search",
    "sync_multi_search_with_dependency_hop",
]
