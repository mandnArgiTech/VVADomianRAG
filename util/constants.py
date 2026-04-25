"""util/constants.py — Shared constants for VVADomainRAG."""

from __future__ import annotations

import os

DIM_TO_MODEL: dict[int, str] = {
    1024: "mxbai-embed-large",
    768: "nomic-embed-text",
}

LANG_TAG: dict[str, str] = {
    ".py": "python",
    ".java": "java",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".jsx": "jsx",
    ".cs": "csharp",
    ".cpp": "cpp",
    ".c": "c",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".kt": "kotlin",
    ".scala": "scala",
    ".sql": "sql",
    ".sh": "bash",
    ".ps1": "powershell",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".json": "json",
    ".xml": "xml",
    ".html": "html",
    ".md": "markdown",
    ".proto": "protobuf",
    ".properties": "properties",
}

TOP_K_DEFAULT = int(os.environ.get("TOP_K", "5"))
MAX_K = max(1, int(os.environ.get("MCP_MAX_K", "25")))
RESULT_CHUNK_MAX_CHARS = max(512, int(os.environ.get("MCP_RESULT_CHUNK_MAX_CHARS", "4096")))
RESULT_CONTEXT_WINDOW_MAX_CHARS = max(
    RESULT_CHUNK_MAX_CHARS,
    int(os.environ.get("MCP_RESULT_CONTEXT_WINDOW_MAX_CHARS", "16000")),
)
HYBRID_SEARCH = os.environ.get("HYBRID_SEARCH", "1").strip().lower() not in ("0", "false", "no")
RRF_K = float(os.environ.get("RRF_K", "60"))
RAG_QUERY_SHARED_EMBED = os.environ.get("RAG_QUERY_SHARED_EMBED", "1").strip().lower() not in (
    "0",
    "false",
    "no",
)
QUERY_DEP_MAX_TOKENS = max(0, int(os.environ.get("QUERY_DEP_MAX_TOKENS", "16")))
QUERY_DEP_MAX_HITS = max(0, int(os.environ.get("QUERY_DEP_MAX_HITS", "10")))
QUERY_DEP_LOOKUP_K = max(1, int(os.environ.get("QUERY_DEP_LOOKUP_K", "2")))
QUERY_CALLER_MAX_HITS = max(0, int(os.environ.get("QUERY_CALLER_MAX_HITS", "10")))
GOD_MODE_MIN_CONTENT_SIZE = 50
