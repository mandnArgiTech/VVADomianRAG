"""
util/constants.py — Shared constants for VVADomainRAG.

Single source of truth for DIM_TO_MODEL and LANG_TAG, which were previously
duplicated across query.py and mcp_server.py.
"""

from __future__ import annotations

# Embedding dimension → Ollama model name.
# Extend here when adding new embedding models.
DIM_TO_MODEL: dict[int, str] = {
    1024: "mxbai-embed-large",
    768: "nomic-embed-text",
}

# File extension → Markdown/code-fence language tag.
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
