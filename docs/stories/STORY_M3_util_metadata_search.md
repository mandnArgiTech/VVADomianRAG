# STORY M3 — util/chunk_metadata.py + util/search_primitives.py

**Branch:** `ngspice_rag`  
**Status:** 🔲 TODO  
**Depends on:** M1 (util/constants.py must exist first)

---

## Context

Six small helpers are copy-pasted in both `query.py` and `mcp_server.py`:
metadata token splitting, dependency-hop filter building, collection routing,
and the dense-search wrapper.  This story extracts them.

---

## M3-A  Create `util/chunk_metadata.py`

### Imports

```python
"""util/chunk_metadata.py — Metadata field parsing for RAG chunks."""
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
```

### Functions — copy verbatim from `query.py` (canonical versions)

#### `_metadata_pipe_or_comma_tokens` → export as `metadata_pipe_or_comma_tokens`

```python
def metadata_pipe_or_comma_tokens(raw: str) -> List[str]:
    """Split pipe- or comma-delimited metadata fields (calls, concepts)."""
    s = (raw or "").strip()
    if not s:
        return []
    if s.startswith("|"):
        return [x.strip() for x in s.strip("|").split("|") if x.strip()]
    return [x.strip() for x in s.split(",") if x.strip()]
```

#### `_parse_dependency_tokens` → export as `parse_dependency_tokens`

Copy body verbatim from `query.py`.

#### `_depend_stems_from_results` → export as `depend_stems_from_results`

Use the **`query.py` body** — it adds `Path(rel.replace("\\", "/")).name` to
stems (the `mcp_server.py` version omits this; the query.py version is more
complete).

Signature:
```python
def depend_stems_from_results(
    results: List[Tuple[Any, Optional[float], str]],
) -> List[str]:
```

#### `_dependencies_where_comma_token` → export as `dependencies_where_comma_token`

Both files are identical — copy either verbatim:

```python
def dependencies_where_comma_token(stem: str) -> Dict[str, Any]:
    """Chroma $or filter matching stem as a whole comma-delimited entry."""
    s = (stem or "").strip()
    if not s:
        return {"dependencies": {"$eq": "__empty_dependency_stem__"}}
    return {
        "$or": [
            {"dependencies": {"$eq": s}},
            {"dependencies": {"$contains": f"{s}, "}},
            {"dependencies": {"$contains": f", {s}, "}},
            {"dependencies": {"$contains": f", {s}"}},
        ]
    }
```

#### `iter_concept_ids`

```python
def iter_concept_ids(concepts_field: str) -> List[str]:
    """Split the concepts metadata field — re-export for single import location."""
    return metadata_pipe_or_comma_tokens(concepts_field)
```

---

## M3-B  Create `util/search_primitives.py`

### Imports

```python
"""util/search_primitives.py — Stateless search building blocks."""
from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from langchain_chroma import Chroma
from util.constants import RAG_QUERY_SHARED_EMBED
```

### `SearchHit` dataclass

Copy **verbatim** from `query.py`:

```python
@dataclass
class SearchHit:
    content: str
    score: Optional[float]
    source_type: str
    metadata: Dict[str, Any]
    collection: Optional[str] = None
    retrieval_hop: Optional[str] = None
```

### `domain_filter`

Both files are identical — copy verbatim:

```python
def domain_filter(names: List[str], domain: str) -> List[str]:
    d = (domain or "").lower().strip()
    if not d:
        return names
    return [n for n in names if n.lower().startswith(d + "_") or n.lower() == d]
```

### `select_collection_names`

The two versions differ only in a minor `troubleshoot` branch detail.
Use the **`query.py` version** (it is the longer, more complete one).

Signature:
```python
def select_collection_names(
    cmap: Dict[str, Chroma], search_type: str, domain: str
) -> List[str]:
```

### `hybrid_candidate_cap`

Both files identical — copy verbatim:

```python
def hybrid_candidate_cap(k: int, env_var: str) -> int:
    import os
    raw = os.environ.get(env_var, "").strip()
    if raw.isdigit():
        return max(1, int(raw))
    return max(40, k * 4)
```

### `shared_query_embedding`

Copy verbatim from `query.py` (`_shared_query_embedding`).  Export as
`shared_query_embedding`.

### `similarity_search_with_score`

Copy verbatim from `query.py` (`_similarity_search_with_score_efficient`).
Export as `similarity_search_with_score`.

---

## M3-C  Update `query.py`

1. Add imports (after M2 imports):
```python
from util.chunk_metadata import (
    metadata_pipe_or_comma_tokens as _metadata_pipe_or_comma_tokens,
    parse_dependency_tokens as _parse_dependency_tokens,
    depend_stems_from_results as _depend_stems_from_results,
    dependencies_where_comma_token as _dependencies_where_comma_token,
    iter_concept_ids,
)
from util.search_primitives import (
    SearchHit,
    domain_filter as _domain_filter,
    select_collection_names as _select_collection_names,
    hybrid_candidate_cap as _hybrid_candidate_cap,
    shared_query_embedding as _shared_query_embedding,
    similarity_search_with_score as _similarity_search_with_score_efficient,
)
```

2. **Delete** from `query.py`:
   - `_metadata_pipe_or_comma_tokens` body (~L78–L85)
   - `@dataclass class SearchHit` block (~L770–L780)
   - `_shared_query_embedding` body (~L782–L797)
   - `_similarity_search_with_score_efficient` body (~L799–L825)
   - `_domain_filter` body (L744–L748)
   - `_hybrid_candidate_cap` body (L339–L343)
   - `_select_collection_names` body (L751–L772)
   - `_parse_dependency_tokens` body (~L1095–L1105)
   - `_depend_stems_from_results` body (L1131–L1146)
   - `_dependencies_where_comma_token` body (L1149–L1161)

3. **KEEP** in `query.py` (these are query-specific):
   - `_exact_chunk_name_hits` (calls `_god_mode_chunk_name_matches` which is query-local)
   - `_sync_multi_search` (uses `_load_symbols_vocab`, `_expand_query_typos`, `_resolve_db_abs`)
   - `_sync_multi_search_with_dependency_hop`
   - `_sync_fetch_dependents`
   - `_sync_fetch_callers`

---

## M3-D  Update `mcp_server.py`

1. Add imports:
```python
from util.chunk_metadata import (
    depend_stems_from_results as _depend_stems_from_results,
    dependencies_where_comma_token as _dependencies_where_comma_token,
    iter_concept_ids,
)
from util.search_primitives import (
    SearchHit,
    domain_filter as _domain_filter,
    select_collection_names as _select_collection_names,
    hybrid_candidate_cap as _hybrid_candidate_cap,
)
```

2. **Delete** from `mcp_server.py`:
   - `_domain_filter` body (L565–L570)
   - `_hybrid_candidate_cap` body (L572–L577)
   - `_select_collection_names` body (L579–L597)
   - `_depend_stems_from_results` body (L804–L820)
   - `_dependencies_where_comma_token` body (L823–L835)

3. Remove the `from query import (SearchHit, ...)` import line — `SearchHit`
   now comes from `util.search_primitives`.  Keep only what is still needed
   from query:
```python
from query import (
    GOD_MODE_MIN_CONTENT_SIZE,
    _god_mode_chunk_name_matches,
    _load_symbols_vocab,
)
```

4. **KEEP** in `mcp_server.py`:
   - `_sync_multi_search` (uses `_structural_importance_int`, `_doc_dedup_key`, `_exact_chunk_name_results`)
   - `_sync_multi_search_with_dependency_hop`
   - `_sync_fetch_dependents`
   - `_sync_fetch_callers`

---

## Acceptance Criteria

- [ ] `util/chunk_metadata.py` exports: `metadata_pipe_or_comma_tokens`, `parse_dependency_tokens`, `depend_stems_from_results`, `dependencies_where_comma_token`, `iter_concept_ids`
- [ ] `util/search_primitives.py` exports: `SearchHit`, `domain_filter`, `select_collection_names`, `hybrid_candidate_cap`, `shared_query_embedding`, `similarity_search_with_score`
- [ ] `query.py`: no local `SearchHit`, `_domain_filter`, `_hybrid_candidate_cap`, `_select_collection_names`, `_depend_stems_from_results`, `_dependencies_where_comma_token`, `_shared_query_embedding`, `_similarity_search_with_score_efficient` bodies
- [ ] `mcp_server.py`: no local `_domain_filter`, `_hybrid_candidate_cap`, `_select_collection_names`, `_depend_stems_from_results`, `_dependencies_where_comma_token` bodies
- [ ] `mcp_server.py` no longer imports `SearchHit` from `query` — imports from `util.search_primitives`
- [ ] `python3 -c "from util.search_primitives import SearchHit, domain_filter; print('OK')"` passes
- [ ] `python3 -c "import ast; [ast.parse(open(f).read()) for f in ['query.py','mcp_server.py','util/chunk_metadata.py','util/search_primitives.py']]; print('ALL OK')"` passes
- [ ] Neither util module imports from `query.py` or `mcp_server.py`
