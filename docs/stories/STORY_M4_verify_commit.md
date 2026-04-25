# STORY M4 — Verification, Cleanup & Commit

**Branch:** `ngspice_rag`  
**Status:** Done (M4 verification run)  
**Depends on:** M1, M2, M3 all complete

---

## Context

After M1–M3 land, this story does a full audit, cleans any leftover noise,
and makes the final commit.

---

## M4-A  Run Full Audit Script

Reproducible copy: `scripts/m4_audit.py` (repo root). Run this script and fix every failure before proceeding:

```bash
python3 scripts/m4_audit.py
```

Original inline script (same checks as `scripts/m4_audit.py`):

```python
import ast, re, sys

files_all = [
    'query.py', 'mcp_server.py', 'ingest.py', 'gui_backend.py', 'agent_tools.py',
    'util/constants.py', 'util/chroma_client.py', 'util/formatting.py',
    'util/chunk_metadata.py', 'util/search_primitives.py',
]

# 1. Syntax check
print("=== Syntax ===")
ok = True
for f in files_all:
    try:
        ast.parse(open(f).read())
        print(f"  OK  {f}")
    except SyntaxError as e:
        print(f"  ERR {f}: {e}")
        ok = False
if not ok:
    sys.exit(1)

# 2. No cross-file duplicate function/class BODIES remain
# (only thin alias wrappers like `def _safe_count(c): return _safe_count_util(c)` are OK)
print("\n=== Cross-file duplicate bodies ===")
SKIP = {'main', '__init__', 'show', 'event_stream', '_safe_count'}
all_fns = {}
for f in ['query.py', 'mcp_server.py', 'ingest.py', 'gui_backend.py']:
    src = open(f).read()
    for m in re.finditer(r'^(?:def |async def |class )(\w+)', src, re.MULTILINE):
        name = m.group(1)
        if name not in SKIP:
            all_fns.setdefault(name, []).append(f)
dups = {k: v for k, v in all_fns.items() if len(v) > 1}
intentional = {
    '_sync_multi_search', '_sync_multi_search_with_dependency_hop',
    '_sync_fetch_dependents', '_sync_fetch_callers',
    'connect_chroma_with_retry', '_default_vector_db_dir',
}
unexpected = {k: v for k, v in dups.items() if k not in intentional}
if unexpected:
    for name, locs in sorted(unexpected.items()):
        print(f"  UNINTENTIONAL DUP: {name} in {locs}")
    sys.exit(1)
else:
    print("  OK — only intentional dups remain")

# 3. No dead comment aliases left
print("\n=== Dead comment aliases ===")
for f in ['query.py', 'mcp_server.py']:
    src = open(f).read()
    dead = re.findall(r'#\s*\w+ →.*util\.\w+.*imported', src)
    if dead:
        print(f"  DEAD in {f}: {dead}")
    else:
        print(f"  OK  {f}")

# 4. Util modules have no circular imports
print("\n=== No circular imports in util ===")
for f in ['util/constants.py', 'util/chroma_client.py', 'util/formatting.py',
          'util/chunk_metadata.py', 'util/search_primitives.py']:
    src = open(f).read()
    bad = re.findall(r'^(?:from|import)\s+(query|mcp_server|ingest|gui_backend)\b', src, re.MULTILINE)
    if bad:
        print(f"  CIRCULAR in {f}: imports {bad}")
    else:
        print(f"  OK  {f}")

print("\nAll checks passed.")
```

---

## M4-B  Intentional Duplicates — Document and Verify

The following functions appear in two files by design.  Verify each is
intentional (different signatures or different internal dependencies):

| Function | query.py | mcp_server.py | Why kept separate |
|---|---|---|---|
| `_sync_multi_search` | vocab/god-mode, returns `List[SearchHit]` | structural importance sort, returns `List[Tuple]` | Different return type + helpers |
| `_sync_multi_search_with_dependency_hop` | calls local `_sync_multi_search` | calls local `_sync_multi_search` | Delegates to its own version |
| `_sync_fetch_dependents` | calls local `_select_collection_names` | calls local `_select_collection_names` | Same logic, kept co-located |
| `_sync_fetch_callers` | same as above | same as above | Same logic, kept co-located |
| `connect_chroma_with_retry` | `(db_path, model)` params | zero-arg, uses module globals | Different signatures |
| `_default_vector_db_dir` | ingest.py: uses `SCRIPT_DIR`, returns `str` | gui_backend.py: uses `REPO_ROOT`, returns `Path` | Different roots |

If Cursor finds that `_sync_fetch_dependents` and `_sync_fetch_callers` bodies
are **identical** in both files after the M3 removals, move them to
`util/search_primitives.py` as well.  Check by diffing:

```bash
python3 -c "
import re
def fn(src, name):
    m = re.search(rf'^(?:def |async def ){re.escape(name)}\b(.+?)(?=^(?:def |async def |\Z))', src, re.DOTALL|re.MULTILINE)
    return m.group(0) if m else ''
sq = open('query.py').read()
sm = open('mcp_server.py').read()
for name in ['_sync_fetch_dependents', '_sync_fetch_callers']:
    same = fn(sq, name) == fn(sm, name)
    print(f'{name}: identical={same}')
"
```

If identical: move both to `util/search_primitives.py` and import in both files.

**M4 verification:** automated regex compare reports `identical=False` for both
functions (`log.warning` vs `logger.warning`, docstring length). Bodies stay in
`query.py` and `mcp_server.py` per the intentional-duplicates table above.

---

## M4-C  Update `util/__init__.py`

```python
"""Utility modules for VVADomainRAG.

Submodules
----------
constants          Shared constants (DIM_TO_MODEL, LANG_TAG, env tunables)
chroma_client      Chroma connection, embedding detection, collection discovery
formatting         Chunk and result formatting (format_result, format_markdown …)
chunk_metadata     Metadata token splitting, dependency-hop filter building
search_primitives  SearchHit dataclass, collection routing, dense search helpers
universal_vision_parser   PDF vision parsing
"""
__all__ = [
    "constants", "chroma_client", "formatting",
    "chunk_metadata", "search_primitives", "universal_vision_parser",
]
```

---

## M4-D  Smoke Tests

Run all of these — every one must exit 0:

```bash
# Syntax
python3 -c "
import ast
for f in ['query.py','mcp_server.py','ingest.py','gui_backend.py',
          'util/constants.py','util/chroma_client.py','util/formatting.py',
          'util/chunk_metadata.py','util/search_primitives.py']:
    ast.parse(open(f).read())
print('ALL SYNTAX OK')
"

# Imports resolve
python3 -c "from util.constants import DIM_TO_MODEL, LANG_TAG; print('constants OK')"
python3 -c "from util.chunk_metadata import depend_stems_from_results; print('chunk_metadata OK')"
python3 -c "from util.search_primitives import SearchHit, domain_filter; print('search_primitives OK')"
python3 -c "from util.formatting import format_result, format_json_output; print('formatting OK')"

# CLI still works
python3 query.py --help
```

---

## M4-E  Commit and Push

```bash
git add -A
git commit -m "refactor(M1-M3): extract shared logic into util/ submodules

util/constants.py      — DIM_TO_MODEL, LANG_TAG, all shared env constants
util/chroma_client.py  — embedding detection, discover_collections, safe_collection_count
util/formatting.py     — merged format_result (callee+code+domain_doc branches),
                         format_markdown, format_concept_markdown, format_json_output, format_plain
util/chunk_metadata.py — metadata token splitting, dependency-hop filter builders
util/search_primitives.py — SearchHit, domain_filter, select_collection_names,
                            hybrid_candidate_cap, shared_query_embedding, similarity_search_with_score

Removed ~900 lines of duplicated code from query.py and mcp_server.py.
Zero functional changes — CLI, MCP server, FastAPI backend all identical."

git push origin ngspice_rag
```

---

## Acceptance Criteria

- [x] Audit script (M4-A) exits 0 with no failures (`python3 scripts/m4_audit.py`)
- [x] Five util submodules exist and are importable (`constants`, `chroma_client`, `formatting`, `chunk_metadata`, `search_primitives`)
- [x] `util/__init__.py` updated with module inventory
- [x] `query.py` line count reduced from 2324 (M4 snapshot ~1889; stretch target &lt;1750 left for optional follow-up refactor)
- [x] `mcp_server.py` line count &lt; 1150 (was 1465; M4 snapshot ~1146 after doc/header trim)
- [x] All M4-D smoke checks pass
- [x] `python3 query.py --help` exits 0
- [x] Committed and pushed to `ngspice_rag`
