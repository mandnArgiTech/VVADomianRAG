# STORY M1 — util/constants.py + util/chroma_client.py

**Branch:** `ngspice_rag`  
**Status:** Done (verified)  
**Depends on:** nothing (create from scratch)

---

## Context

`query.py` and `mcp_server.py` copy-paste the same constants and Chroma
connection helpers.  This story extracts them into two tiny util modules.
No logic changes — pure move.

---

## M1-A  Create `util/constants.py`

Create the file. Copy these definitions **verbatim** from `query.py`
(it is the reference; mcp_server.py copies are identical or subsets):

```python
"""util/constants.py — Shared constants for VVADomainRAG."""
from __future__ import annotations
import os

DIM_TO_MODEL: dict[int, str] = {
    1024: "mxbai-embed-large",
    768:  "nomic-embed-text",
}

LANG_TAG: dict[str, str] = {
    ".py": "python", ".java": "java", ".js": "javascript",
    ".ts": "typescript", ".tsx": "tsx", ".jsx": "jsx",
    ".cs": "csharp", ".cpp": "cpp", ".c": "c", ".go": "go",
    ".rs": "rust", ".rb": "ruby", ".kt": "kotlin",
    ".scala": "scala", ".sql": "sql", ".sh": "bash",
    ".ps1": "powershell", ".yml": "yaml", ".yaml": "yaml",
    ".json": "json", ".xml": "xml", ".html": "html",
    ".md": "markdown", ".proto": "protobuf",
    ".properties": "properties",
}

TOP_K_DEFAULT       = int(os.environ.get("TOP_K", "5"))
MAX_K               = max(1, int(os.environ.get("MCP_MAX_K", "25")))
RESULT_CHUNK_MAX_CHARS = max(512, int(os.environ.get("MCP_RESULT_CHUNK_MAX_CHARS", "4096")))
RESULT_CONTEXT_WINDOW_MAX_CHARS = max(
    RESULT_CHUNK_MAX_CHARS,
    int(os.environ.get("MCP_RESULT_CONTEXT_WINDOW_MAX_CHARS", "16000")),
)
HYBRID_SEARCH       = os.environ.get("HYBRID_SEARCH", "1").strip().lower() not in ("0", "false", "no")
RRF_K               = float(os.environ.get("RRF_K", "60"))
RAG_QUERY_SHARED_EMBED = os.environ.get("RAG_QUERY_SHARED_EMBED", "1").strip().lower() not in ("0", "false", "no")
QUERY_DEP_MAX_TOKENS = max(0, int(os.environ.get("QUERY_DEP_MAX_TOKENS", "16")))
QUERY_DEP_MAX_HITS  = max(0, int(os.environ.get("QUERY_DEP_MAX_HITS", "10")))
QUERY_DEP_LOOKUP_K  = max(1, int(os.environ.get("QUERY_DEP_LOOKUP_K", "2")))
QUERY_CALLER_MAX_HITS = max(0, int(os.environ.get("QUERY_CALLER_MAX_HITS", "10")))
GOD_MODE_MIN_CONTENT_SIZE = 50
```

---

## M1-B  Create `util/chroma_client.py`

Create the file with these functions.

### `embedding_model_from_db_path`

Take the body from **`mcp_server.py` L68–L174** (it is the complete version;
`query.py` delegates to it).  The function reads `ingestion_config.json` first,
then probes Chroma embedding dims, then defaults to `"nomic-embed-text"`.

Signature:
```python
def embedding_model_from_db_path(db_path: str) -> str: ...
```

### `detect_embedding_model`

```python
def detect_embedding_model(db_path: str) -> str:
    env_val = os.environ.get("EMBEDDING_MODEL", "").strip()
    if env_val:
        return env_val
    return embedding_model_from_db_path(db_path)
```

### `persistent_chroma_client`

Copy verbatim from `query.py` (`_persistent_chroma_client`).  Name it
`persistent_chroma_client` (drop the leading underscore — it is now a public
util).

### `discover_collections`

Use the **`query.py` body** (it is more complete — has the empty-collection
warning and the `create_collection_if_not_exists=False` guard).  Signature
stays `(db_path, embeddings, chroma_client=None) -> Dict[str, Chroma]`.

### `safe_collection_count`

```python
def safe_collection_count(coll: Any) -> int:
    try:
        return int(coll.count())
    except Exception:
        return 0
```

### Imports for the module

```python
from __future__ import annotations
import json, logging, os, time
from typing import Any, Dict, Optional, Tuple
import chromadb
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from util.constants import DIM_TO_MODEL
```

---

## M1-C  Update `query.py`

1. Add at the top (after `from reranker import ...`):
```python
from util.constants import (
    DIM_TO_MODEL, LANG_TAG, TOP_K_DEFAULT, MAX_K,
    RESULT_CHUNK_MAX_CHARS, RESULT_CONTEXT_WINDOW_MAX_CHARS,
    HYBRID_SEARCH, RRF_K, RAG_QUERY_SHARED_EMBED,
    QUERY_DEP_MAX_TOKENS, QUERY_DEP_MAX_HITS, QUERY_DEP_LOOKUP_K,
    QUERY_CALLER_MAX_HITS, GOD_MODE_MIN_CONTENT_SIZE,
)
from util.chroma_client import (
    detect_embedding_model,
    embedding_model_from_db_path,
    persistent_chroma_client as _persistent_chroma_client,
    discover_collections,
    safe_collection_count as _safe_count_util,
)
```

2. **Delete** the following constant blocks from `query.py` (they now come from util):
   - `DIM_TO_MODEL = {...}` (L64–L67)
   - `TOP_K_DEFAULT`, `MAX_K`, `RESULT_CHUNK_MAX_CHARS`, `RESULT_CONTEXT_WINDOW_MAX_CHARS` (L69–L74)
   - `HYBRID_SEARCH`, `RRF_K`, `RAG_QUERY_SHARED_EMBED` (L91–L97)
   - `QUERY_DEP_MAX_TOKENS`, `QUERY_DEP_MAX_HITS`, `QUERY_DEP_LOOKUP_K`, `QUERY_CALLER_MAX_HITS` (L101–L104)
   - `GOD_MODE_MIN_CONTENT_SIZE = 50` (L113)
   - `LANG_TAG = {...}` (L293–L318)

3. **Delete** these function bodies (now from util):
   - `embedding_model_from_db_path` (L399–L415)
   - `detect_embedding_model` (L417–L421)
   - `_persistent_chroma_client` (L228–L241) — already imported as alias
   - `discover_collections` (L551–L589)

4. Replace `_safe_count` thin wrapper:
```python
def _safe_count(coll) -> int:
    return _safe_count_util(coll)
```

---

## M1-D  Update `mcp_server.py`

1. Add imports (after `from reranker import ...`):
```python
from util.constants import (
    DIM_TO_MODEL, LANG_TAG,
    RESULT_CHUNK_MAX_CHARS, RESULT_CONTEXT_WINDOW_MAX_CHARS,
    HYBRID_SEARCH, RRF_K,
    QUERY_DEP_MAX_TOKENS, QUERY_DEP_MAX_HITS, QUERY_DEP_LOOKUP_K,
    QUERY_CALLER_MAX_HITS,
)
from util.chroma_client import (
    detect_embedding_model,
    embedding_model_from_db_path,
    discover_collections,
    safe_collection_count as _safe_count_chroma_util,
)
```

2. **Delete** from `mcp_server.py`:
   - `DIM_TO_MODEL = {...}` (L62–L67)
   - `LANG_TAG = {...}` (L136–L160)
   - `HYBRID_SEARCH`, `RRF_K`, `QUERY_DEP_*`, `QUERY_CALLER_MAX_HITS` (L112–L118)
   - `RESULT_CHUNK_MAX_CHARS`, `RESULT_CONTEXT_WINDOW_MAX_CHARS` (L104–L108)
   - `detect_embedding_model` function body (L68–L96)
   - `discover_collections` function body (L252–L283)

3. Keep `EMBEDDING_MODEL = detect_embedding_model(DB_PATH)` — it now calls the
   util version.  Keep the local `connect_chroma_with_retry()` (zero-arg, uses
   module globals — it is NOT a duplicate, just calls util's `discover_collections`).

4. Keep `_safe_count_chroma` (it operates on a LangChain `Chroma` object, not a
   raw collection; it is a different function from `safe_collection_count`).

---

## M1-E  Update `ingest.py`

Add import and replace `_safe_count` body:
```python
from util.chroma_client import safe_collection_count as _safe_count_util
# ...
def _safe_count(coll) -> int:
    return _safe_count_util(coll)
```

---

## Acceptance Criteria

- [x] `util/constants.py` exists, exports all 14 names listed above
- [x] `util/chroma_client.py` exists, exports 5 functions
- [x] `query.py`: no local `DIM_TO_MODEL`, `LANG_TAG`, or env-constant blocks; no `detect_embedding_model`/`discover_collections` bodies
- [x] `mcp_server.py`: no local `DIM_TO_MODEL`, `LANG_TAG`, or duplicated env-constant blocks; no `detect_embedding_model`/`discover_collections` bodies
- [x] `python3 -c "from util.constants import DIM_TO_MODEL, LANG_TAG; print('OK')"` passes
- [x] `python3 -c "from util.chroma_client import detect_embedding_model; print('OK')"` passes
- [x] `python3 -c "import ast; [ast.parse(open(f).read()) for f in ['query.py','mcp_server.py','ingest.py','util/constants.py','util/chroma_client.py']]; print('ALL OK')"` passes
- [x] No circular imports — util modules do NOT import from query.py or mcp_server.py
