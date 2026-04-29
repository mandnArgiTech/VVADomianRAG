"""Query-layer tuning (env-driven) and exit codes — portable across CLI / GUI / MCP."""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_TIMEOUT = int(os.environ.get("QUERY_CLI_TIMEOUT", "120"))

HISTORY_FILE = Path.home() / ".rag_query_history"

RAG_CONTEXT_MAX_CHARS = max(4096, int(os.environ.get("RAG_CONTEXT_MAX_CHARS", "32000")))
QUERY_PROMPT_TOP_M = max(1, int(os.environ.get("QUERY_PROMPT_TOP_M", "5")))
QUERY_PROMPT_DOC_THRESHOLD = float(os.environ.get("QUERY_PROMPT_DOC_THRESHOLD", "0.6"))

EXIT_OK = 0
EXIT_NO_RESULTS = 1
EXIT_ARG = 2
EXIT_INFRA = 3

DEFAULT_CHAT_LLM = "gemma3:27b-it-qat"
CHAT_MODEL_FALLBACKS = [
    "gemma3:27b-it-qat",
    "gemma3:27b",
    "gemma3:12b-it-qat",
    "gemma3:12b",
    "qwen2.5-coder:32b",
    "llama3",
    "mistral",
]
