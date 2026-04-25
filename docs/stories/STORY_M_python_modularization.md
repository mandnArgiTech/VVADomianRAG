# STORY M — Python Codebase Modularization

**Repository:** `mandnArgiTech/VVADomianRAG` (branch `ngspice_rag`)  
**Status:** 🔲 TODO — Implement in full  
**Scope:** All 10 root-level Python files  
**Goal:** Super modular, reusable, logically structured components — zero functional breakage

---

## Problem Statement

The 10 root-level Python files contain massive duplication and no shared module layer.
The same logic is copy-pasted across files, making maintenance a nightmare.

### Current file sizes (lines)

| File | Lines | Role |
|------|-------|------|
| `ingest.py` | 5120 | Ingestion pipeline |
| `gui_backend.py` | 3400 | FastAPI backend |
| `query.py` | 2324 | CLI query engine |
| `agent_tools.py` | 644 | Agent tool dispatch |
| `hybrid_search.py` | 265 | BM25 + RRF search |
| `downloadrfc.py` | 210 | RFC downloader |
| `reranker.py` | 153 | Cross-encoder reranker |
| `mcp_server.py` | 1465 | MCP server |
| `sanitizer.py` | 31 | Text sanitizer |
| `domain_feeder.py` | 10 | Domain doc feeder |

---

## Confirmed Duplications (verified from source)

### Constants duplicated in `query.py` AND `mcp_server.py`

```
DIM_TO_MODEL            — dict: embedding dim → model name
LANG_TAG                — dict: file extension → fence language tag
HYBRID_SEARCH           — bool env flag
RRF_K                   — float env constant
QUERY_DEP_MAX_HITS      — int env constant
QUERY_DEP_MAX_TOKENS    — int env constant
QUERY_DEP_LOOKUP_K      — int env constant
QUERY_CALLER_MAX_HITS   — int env constant
RESULT_CHUNK_MAX_CHARS  — int env constant
RESULT_CONTEXT_WINDOW_MAX_CHARS — int env constant
TOP_K_DEFAULT           — int constant
```

### Functions duplicated in `query.py` AND `mcp_server.py`

```
detect_embedding_model(db_path)
discover_collections(db_path, embeddings, chroma_client)
connect_chroma_with_retry(...)         — NOTE: different signatures, see constraints
_infer_source_type(meta)
_fence_for(content)
_truncate_chunk(text, max_chars)
format_result(doc, score, source_type)  — NOTE: diverged implementations, see below
_domain_filter(names, domain)
_hybrid_candidate_cap(k, env_var)
_select_collection_names(cmap, search_type, domain)
_depend_stems_from_results(results)
_dependencies_where_comma_token(stem)
_sync_fetch_dependents(primary, search_type, domain, repo_filter, cmap, max_hits)
_sync_fetch_callers(primary, search_type, domain, repo_filter, cmap, max_hits)
_sync_multi_search(...)                — NOTE: different implementations, see constraints
_sync_multi_search_with_dependency_hop(...) — NOTE: delegates to local _sync_multi_search
```

### Functions duplicated elsewhere

```
_safe_count(coll)          — query.py AND ingest.py
_default_vector_db_dir()   — ingest.py AND gui_backend.py (different roots, see constraints)
search_codebase(...)        — mcp_server.py AND agent_tools.py (different implementations)
```

---

## Target Architecture — `util/` submodules

Create the following modules inside the existing `util/` directory.  
`util/__init__.py` already exists — update it with the module inventory.

### `util/constants.py`
Single source of truth for all shared constants.

```python
# Embedding dimension → model name
DIM_TO_MODEL: dict[int, str] = {
    1024: "mxbai-embed-large",
    768: "nomic-embed-text",
}

# File extension → Markdown fence language tag
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

# Search tuning — all overridable via env vars
HYBRID_SEARCH: bool = os.environ.get("HYBRID_SEARCH", "1").strip().lower() not in ("0", "false", "no")
RRF_K: float = float(os.environ.get("RRF_K", "60"))
QUERY_DEP_MAX_HITS: int = max(0, int(os.environ.get("QUERY_DEP_MAX_HITS", "10")))
QUERY_DEP_MAX_TOKENS: int = max(0, int(os.environ.get("QUERY_DEP_MAX_TOKENS", "0")))
QUERY_DEP_LOOKUP_K: int = max(1, int(os.environ.get("QUERY_DEP_LOOKUP_K", "2")))
QUERY_CALLER_MAX_HITS: int = max(0, int(os.environ.get("QUERY_CALLER_MAX_HITS", "10")))
RESULT_CHUNK_MAX_CHARS: int = max(512, int(os.environ.get("MCP_RESULT_CHUNK_MAX_CHARS", "4096")))
RESULT_CONTEXT_WINDOW_MAX_CHARS: int = max(
    RESULT_CHUNK_MAX_CHARS,
    int(os.environ.get("MCP_RESULT_CONTEXT_WINDOW_MAX_CHARS", "16000")),
)
TOP_K_DEFAULT: int = int(os.environ.get("RAG_TOP_K_DEFAULT", "8"))
```

### `util/chroma_client.py`
All ChromaDB connection, collection discovery, and embedding detection logic.

**Functions to extract (take the body verbatim from `query.py` as the reference — it is more complete):**

```
persistent_chroma_client(path: str) -> chromadb.PersistentClient
embedding_model_from_db_path(db_path: str) -> str
detect_embedding_model(db_path: str) -> str
discover_collections(db_path, embeddings, chroma_client=None) -> Dict[str, Chroma]
connect_chroma_with_retry(db_path: str, model: str) -> Tuple[PersistentClient, OllamaEmbeddings, Dict[str, Chroma]]
safe_collection_count(coll: Any) -> int
```

**Important:** `connect_chroma_with_retry` in `util/chroma_client.py` must take `(db_path, model)` as parameters.  
Both `query.py` and `mcp_server.py` will keep thin local wrappers:
- `query.py` already calls it as `connect_chroma_with_retry(db_path, model)` → can import directly or keep 1-line wrapper
- `mcp_server.py` calls it with no args using module globals `DB_PATH` and `_shared_embedder` → must keep its own local wrapper that calls `util.chroma_client.discover_collections(DB_PATH, embeddings, chroma_client)` internally

### `util/formatting.py`
All chunk and result formatting logic.

**Functions to extract — take the body verbatim from `query.py` as reference:**

```
infer_source_type(meta: dict) -> str
fence_for(content: str) -> str
truncate_chunk(text: str, max_chars: int = None) -> str
format_result(doc, score, source_type) -> str
format_markdown(hits: List[SearchHit], query: str) -> str
format_concept_markdown(hits: List[SearchHit], concept: str) -> str
format_json_output(query: str, hits: List[SearchHit], mode: str, answer: str = "") -> str
format_plain(hits: List[SearchHit]) -> str
```

**Critical:** `format_result` diverges between `query.py` (78 lines) and `mcp_server.py` (100 lines).  
The `mcp_server.py` version has extra branches for `callee` source_type and surfaces `structural_importance` and `source_c_files`. The merged version in `util/formatting.py` must include ALL branches from both files. Parameters:

```python
def format_result(
    doc,
    score: Optional[float],
    source_type: str,
    *,
    result_chunk_max_chars: int = RESULT_CHUNK_MAX_CHARS,
    result_context_window_max_chars: int = RESULT_CONTEXT_WINDOW_MAX_CHARS,
    metadata_token_fn=None,          # callable(raw_str) -> List[str]
    structural_importance_fn=None,   # callable(meta) -> int, optional
) -> str:
```

**Critical:** `format_json_output` signature from `query.py` is:
```python
def format_json_output(query: str, hits: List[SearchHit], mode: str, answer: str = "") -> str
```
This is the correct signature. Do NOT change it.

### `util/chunk_metadata.py`
All metadata token splitting and dependency-hop filter building.

**Functions to extract (take verbatim from `query.py`):**

```
metadata_pipe_or_comma_tokens(raw: str) -> List[str]
parse_dependency_tokens(deps: str) -> List[str]
depend_stems_from_results(results: List[Tuple[doc, score, str]]) -> List[str]
dependencies_where_comma_token(stem: str) -> Dict[str, Any]
iter_concept_ids(concepts_field: str) -> List[str]    # re-export of ingest.py logic
```

### `util/search_core.py`
The `SearchHit` dataclass plus all stateless search primitives.

**Extract from `query.py` verbatim:**

```
SearchHit                              @dataclass
domain_filter(names, domain) -> List[str]
select_collection_names(cmap, search_type, domain) -> List[str]
hybrid_candidate_cap(k, env_var) -> int
shared_query_embedding(cmap, targets, query) -> Optional[List[float]]
similarity_search_with_score(vs, query, k, flt, q_emb) -> List[Tuple]
```

**Do NOT extract into util/search_core.py:**
- `_sync_multi_search` — stays local in both files (see constraints below)
- `_sync_multi_search_with_dependency_hop` — stays local in both files
- `_sync_fetch_dependents` — stays local in both files
- `_sync_fetch_callers` — stays local in both files
- `_exact_chunk_name_hits` — stays local in `query.py` (calls `_god_mode_chunk_name_matches`)

---

## Hard Constraints — Do NOT Violate

### 1. `_sync_multi_search` must stay local in BOTH files

`query.py` version (keep as-is):
- Uses `_load_symbols_vocab`, `_expand_query_typos`, `_resolve_db_abs` (query-local helpers)
- Uses `_exact_chunk_name_hits` which calls `_god_mode_chunk_name_matches`
- Returns `List[SearchHit]`
- Has BM25 tiebreaking with `bm25_rank`/`dense_rank`

`mcp_server.py` version (keep as-is):
- Uses `_structural_importance_int`, `_doc_dedup_key`, `_exact_chunk_name_results` (mcp-local helpers)
- Returns `List[Tuple[doc, score, str, str]]` (different return type)
- Has callee-expand logic

These two functions are NOT the same. They share sub-helpers that CAN be moved to util (`_domain_filter`, `_hybrid_candidate_cap`, etc.) but the functions themselves stay local.

### 2. `connect_chroma_with_retry` — two completely different signatures

`query.py`: `connect_chroma_with_retry(db_path: str, model: str) -> Tuple[...]`  
`mcp_server.py`: `connect_chroma_with_retry() -> Dict[str, Chroma]` (uses module globals)

The `mcp_server.py` version must stay as a local wrapper. It can internally call `discover_collections` from util, but its zero-arg signature must be preserved.

### 3. `_default_vector_db_dir` — different implementations, keep both local

`ingest.py` version: uses `SCRIPT_DIR` (Path relative to ingest.py itself), returns `str`  
`gui_backend.py` version: uses `REPO_ROOT` (a different local constant), returns `Path`, also calls `.mkdir()`

They cannot share an implementation without knowing their local root variable. Keep both local.

### 4. `_safe_count` — thin alias pattern is acceptable

Both `query.py` and `ingest.py` can keep a `def _safe_count(coll)` that delegates to `util.chroma_client.safe_collection_count`. This is fine — it preserves backward compat for 5000+ lines of internal callers.

### 5. Zero circular imports

`util/` modules must NEVER import from `query.py`, `mcp_server.py`, `ingest.py`, or `gui_backend.py`.  
Allowed imports inside util: `chromadb`, `langchain_*`, `hybrid_search` (for `stable_doc_id`, `get_bm25_index`, `reciprocal_rank_fusion`, `search_bm25_ranked_ids`), `reranker` (for `get_reranker`, `rerank_pool_limit`).

### 6. Preserve all existing public APIs and CLI behaviour

- `python query.py --help` must work identically
- `python mcp_server.py` must start identically  
- `gui_backend.py` FastAPI app must import and start identically
- All `from query import (SearchHit, ...)` imports in `mcp_server.py` must continue to work
  (either `SearchHit` stays in `query.py` as a re-export, or `mcp_server.py` imports from `util.search_core` directly)

---

## Implementation Checklist

### Phase 1 — Create util modules

- [ ] `util/constants.py` — all shared constants
- [ ] `util/chroma_client.py` — Chroma connection + embedding detection
- [ ] `util/formatting.py` — all formatting functions (merged `format_result`)
- [ ] `util/chunk_metadata.py` — metadata token helpers
- [ ] `util/search_core.py` — `SearchHit` + stateless search primitives
- [ ] Update `util/__init__.py` with module inventory

### Phase 2 — Wire imports into source files

- [ ] `query.py` — import from util, remove duplicate bodies (keep local: `_sync_multi_search`, `_sync_multi_search_with_dependency_hop`, `_sync_fetch_dependents`, `_sync_fetch_callers`, `_exact_chunk_name_hits`, `connect_chroma_with_retry`)
- [ ] `mcp_server.py` — import from util, remove duplicate bodies (keep local: `_sync_multi_search`, `_sync_multi_search_with_dependency_hop`, `_sync_fetch_dependents`, `_sync_fetch_callers`, `_exact_chunk_name_results`, `connect_chroma_with_retry`)
- [ ] `ingest.py` — import `safe_collection_count` from util, alias `_safe_count`
- [ ] `gui_backend.py` — no changes needed (it already delegates to `query_mod.*`)
- [ ] `agent_tools.py` — no changes needed

### Phase 3 — Verify

- [ ] `python3 -c "import ast; [ast.parse(open(f).read()) for f in ['query.py','mcp_server.py','ingest.py','gui_backend.py','util/constants.py','util/chroma_client.py','util/formatting.py','util/chunk_metadata.py','util/search_core.py']]; print('ALL OK')"` — must pass
- [ ] No cross-file duplicate function bodies remain (only the 5 intentional ones listed in constraints)
- [ ] No dead comment lines left behind (e.g. `# foo → util.bar`)
- [ ] `python3 query.py --help` exits 0
- [ ] All util module imports resolve (no ImportError)

### Phase 4 — Commit and push

```
git add -A
git commit -m "refactor(M): super modular util/ submodules — zero breakage

Created 5 util/ submodules as single source of truth:
- util/constants.py: DIM_TO_MODEL, LANG_TAG, all shared env constants
- util/chroma_client.py: Chroma connection, embedding detection, discovery
- util/formatting.py: format_result (merged), format_markdown, format_plain, format_json_output
- util/chunk_metadata.py: token splitting, dependency hop filters
- util/search_core.py: SearchHit dataclass + stateless search primitives

Removed ~900 lines of duplicated code from query.py and mcp_server.py.
Zero functional changes — all CLI, MCP, and FastAPI behaviour identical."
git push origin ngspice_rag
```

---

## Acceptance Criteria

- [ ] **AC-1** `util/constants.py` exists and exports `DIM_TO_MODEL`, `LANG_TAG`, and all 9 shared env constants
- [ ] **AC-2** `util/chroma_client.py` exists and exports `detect_embedding_model`, `embedding_model_from_db_path`, `persistent_chroma_client`, `discover_collections`, `connect_chroma_with_retry`, `safe_collection_count`
- [ ] **AC-3** `util/formatting.py` exists and exports `infer_source_type`, `fence_for`, `truncate_chunk`, `format_result` (merged), `format_markdown`, `format_concept_markdown`, `format_json_output`, `format_plain`
- [ ] **AC-4** `util/chunk_metadata.py` exists and exports `metadata_pipe_or_comma_tokens`, `parse_dependency_tokens`, `depend_stems_from_results`, `dependencies_where_comma_token`, `iter_concept_ids`
- [ ] **AC-5** `util/search_core.py` exists and exports `SearchHit`, `domain_filter`, `select_collection_names`, `hybrid_candidate_cap`, `shared_query_embedding`, `similarity_search_with_score`
- [ ] **AC-6** `query.py` imports all moved names from `util.*`, duplicate function bodies removed, line count < 1850
- [ ] **AC-7** `mcp_server.py` imports all moved names from `util.*`, duplicate function bodies removed, line count < 1200
- [ ] **AC-8** `ingest.py` imports `safe_collection_count` from `util.chroma_client`
- [ ] **AC-9** Zero `SyntaxError` across all 10 source files + 5 util modules
- [ ] **AC-10** No circular imports — `util/` modules do not import from root-level source files
- [ ] **AC-11** `python3 query.py --help` exits 0 with no import errors
- [ ] **AC-12** Committed and pushed to `ngspice_rag`
