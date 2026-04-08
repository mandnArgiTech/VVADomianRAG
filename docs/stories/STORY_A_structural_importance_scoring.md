# STORY A: Structural Importance Scoring During Ingest

**Repository:** `mandnArgiTech/VVADomianRAG` branch `ngspice_rag`
**Priority:** High
**Estimated effort:** 3–4 hours
**Files to modify:** `ingest.py`, `mcp_server.py`
**Files to create:** `tests/test_structural_importance.py`

---

## Business Context

VVADomianRAG feeds context to Cursor IDE via MCP when fixing convergence and device-model bugs in the **NodalAI** Python SPICE kernel (`mandnArgiTech/NodalAI`). The ngspice C source (~500K lines) is the reference implementation. When a developer queries "how does ngspice handle GMIN stepping", the RAG retrieves chunks by semantic similarity alone — it has no awareness that `cktdefs.h` (included by 80+ files) is architecturally central, while an isolated test helper is not.

This story adds a **`structural_importance`** integer metadata field to every code chunk at ingest time. The field counts how many other files in the same ingest batch reference the chunk's parent filename (via `#include`, `import`, `from X import`). This lets the MCP server break relevance ties: when two chunks score equally on cosine similarity, the one from the more structurally important file wins.

The same mechanism also works for the **NodalAI Python codebase** itself. `ecad/models.py` and `ecad/spice_netlist.py` are each imported by 12 other files — knowing this helps the RAG prioritize core data-structure definitions over leaf modules.

---

## Scope — What This Story Is

1. A **two-pass ingest** for code mode: first pass collects `#include`/`import` targets per file; second pass (existing) chunks files and stamps each chunk with a `structural_importance` count.
2. A new metadata field `structural_importance` added to `METADATA_KEYS`.
3. MCP server uses this field as a **tiebreaker** when formatting results (not as a Chroma `where` filter — that would be too coarse).

## Scope — What This Story Is NOT

- Not a PageRank algorithm. Simple reference count is sufficient and debuggable.
- Not a separate graph database or networkx dependency.
- Not modifying the chunking logic itself — only metadata enrichment.

---

## Acceptance Criteria

### AC-1: Reference count collection (pre-pass)

**Given** a source directory containing C/C++ and Python files being ingested with `--mode code`,
**When** ingest.py runs,
**Then** before chunking begins, a dictionary `file_ref_counts: Dict[str, int]` is built where:
- Each key is a **filename stem** (e.g., `cktdefs`, `models`, `spice_netlist`)
- Each value is the count of how many distinct source files reference that stem via `#include` (C/C++), `import` (Python/Java), or `from X import` (Python)
- The counting uses the **same regex patterns** already in `extract_dependencies()` (lines 1624–1696 of `ingest.py`) — do NOT duplicate regex logic; refactor `extract_dependencies` to also return the raw stem list

### AC-2: Metadata field added

**Given** the `METADATA_KEYS` list in `ingest.py` (line 118),
**When** this story is complete,
**Then**:
- `"structural_importance"` appears in `METADATA_KEYS` after `"device_family"` (line 182)
- Every code chunk gets `meta["structural_importance"]` set to `str(file_ref_counts.get(path.stem, 0))`
- Non-code chunks (domain docs, RFCs, MIBs) get `"0"`

### AC-3: No performance regression on large codebases

**Given** an ngspice source tree with ~2,000 C/H files,
**When** ingest runs,
**Then** the pre-pass completes in under 5 seconds (it is a single `os.walk` + regex scan, no AST parsing)

### AC-4: MCP result formatting uses importance as tiebreaker

**Given** `mcp_server.py` function `_format_doc()` (around line 395),
**When** formatting a search result document,
**Then**:
- If `structural_importance` metadata is present and > 0, append `(importance: N)` to the header line
- In `_sync_multi_search`, when results from the same collection have **identical** cosine distance (within 0.001), sort the tied group by `structural_importance` descending

### AC-5: Existing tests still pass

**Given** the full pytest suite (`pytest tests/`),
**When** run after this change,
**Then** all existing tests pass with zero failures. The 95% coverage threshold on `ingest.py` is maintained.

---

## Implementation Guide

### Step 1: Refactor `extract_dependencies` to return raw stems

**File:** `ingest.py`, line 1624

Currently `extract_dependencies(content, ext)` returns a formatted comma-separated string. Refactor into two functions:

```python
def _extract_dependency_stems(content: str, ext: str) -> List[str]:
    """Return raw list of dependency stems (filenames/modules) found in content."""
    # Move existing regex logic here. Return raw mods list BEFORE formatting.
    ...

def extract_dependencies(content: str, ext: str) -> str:
    """Extract import-like symbols for metadata (comma-separated)."""
    mods = _extract_dependency_stems(content, ext)
    return _format_dependencies_field(mods)
```

This refactor is safe because `extract_dependencies` is only called at line 3614 and in tests.

### Step 2: Build reference count map in `main_ingest`

**File:** `ingest.py`, inside the `main_ingest` function (starts ~line 3450)

Add a pre-pass **before** the main file loop (before line ~3560 where `for src_key, st, extra in walk_items:` begins):

```python
# --- Pre-pass: structural importance for code mode ---
file_ref_counts: Dict[str, int] = {}
if source_type == "code":
    for pre_path in _iter_source_files(source_dir, ...):  # reuse existing walker
        try:
            raw = pre_path.read_bytes()
            text_pre = raw.decode("utf-8", errors="replace")
        except Exception:
            continue
        stems = _extract_dependency_stems(text_pre, pre_path.suffix.lower())
        for stem in stems:
            # Normalize: strip path components, take filename stem only
            clean = Path(stem).stem  # "ngspice/cktdefs.h" -> "cktdefs"
            file_ref_counts[clean] = file_ref_counts.get(clean, 0) + 1
```

**Critical:** The pre-pass iterates the same file list as the main loop. Reuse the existing file-walking logic. Do NOT re-implement `os.walk` or gitignore filtering — call the same helper that produces `walk_items`.

### Step 3: Stamp chunks with importance

**File:** `ingest.py`, around line 3644 (inside the `for i, (text, partial) in enumerate(pieces):` loop)

After `meta["device_family"]` is set in the base metadata (line 3639), add:

```python
base["structural_importance"] = str(file_ref_counts.get(path.stem, 0))
```

### Step 4: Add to METADATA_KEYS

**File:** `ingest.py`, line 182

Add `"structural_importance"` right after `"device_family"`.

### Step 5: MCP tiebreaker

**File:** `mcp_server.py`

In `_format_doc()` (~line 395), add after the existing metadata header construction:

```python
si = int(meta.get("structural_importance") or 0)
if si > 0:
    header.append(f"**importance:** {si}")
```

In `_sync_multi_search()`, after the final results list is assembled but before truncation to `k`, add a stable sort:

```python
# Tiebreak: among results with same distance (within 0.001), prefer higher structural_importance
def _sort_key(item):
    doc, dist, stype = item
    si = int((getattr(doc, 'metadata', None) or {}).get('structural_importance') or 0)
    return (round(dist or 0.0, 3), -si)
results.sort(key=_sort_key)
```

---

## Test Plan

### File: `tests/test_structural_importance.py`

```
Test ID | Description | Approach
--------|-------------|----------
SI-01   | _extract_dependency_stems returns correct stems for C #include | Feed C content with 3 includes, assert returned stems match
SI-02   | _extract_dependency_stems returns correct stems for Python import | Feed Python content with `from ecad.models import X` and `import numpy`, assert `['ecad', 'numpy']` (top-level stems)
SI-03   | _extract_dependency_stems returns empty list for content with no imports | Feed plain text, assert empty list
SI-04   | extract_dependencies still returns formatted string (backward compat) | Same inputs as SI-01, call extract_dependencies, assert comma-separated output unchanged
SI-05   | file_ref_counts correctly counts C header references | Create tmpdir with 3 .c files: two include "common.h", one includes "util.h". Run pre-pass logic. Assert file_ref_counts["common"] == 2, file_ref_counts["util"] == 1
SI-06   | file_ref_counts correctly counts Python imports | Create tmpdir with: a.py imports models, b.py imports models, c.py imports solver. Assert file_ref_counts["models"] == 2
SI-07   | structural_importance appears in METADATA_KEYS | `assert "structural_importance" in METADATA_KEYS`
SI-08   | Chunks from referenced files get correct importance | Mock a minimal ingest run with 3 files (two reference fileA). Assert chunks from fileA have structural_importance == "2"
SI-09   | Non-code chunks get importance "0" | Ingest a markdown domain doc. Assert structural_importance == "0"
SI-10   | MCP _format_doc includes importance when > 0 | Create a mock Document with metadata structural_importance="5", call _format_doc, assert "importance: 5" in output
SI-11   | MCP _format_doc omits importance when 0 | Create mock Document with structural_importance="0", assert "importance" not in output
SI-12   | Tiebreaker sorts correctly | Create 3 results with same distance 0.15: importance 0, 5, 2. Assert after sort: order is 5, 2, 0
SI-13   | Tiebreaker preserves distance-based ordering | Create results: dist=0.1 importance=1, dist=0.2 importance=10. Assert dist=0.1 still comes first (distance dominates)
```

### Running tests

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest tests/test_structural_importance.py -v
```

### Manual validation

After implementation, run a real ingest on the ngspice source and spot-check:

```bash
./run.sh --mode code --domain spice --source /path/to/ngspice/src
```

Then query via MCP or query CLI:

```bash
./query.sh semantic "CKT circuit struct definition" --domain spice
```

Verify that chunks from `cktdefs.h` show `importance: N` where N > 50 (it's included by most device files). Verify that chunks from an isolated test file show `importance: 0` or `importance: 1`.

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Pre-pass doubles file I/O time | Pre-pass only reads first 8KB per file (imports are always at the top). Add `content[:8192]` limit. |
| Stem normalization mismatches (`cktdefs.h` vs `cktdefs`) | Use `Path(stem).stem` consistently to strip extensions |
| `structural_importance` clutters metadata for non-code domains | Default to `"0"` — Chroma stores strings, cost is negligible |
| Breaking existing `extract_dependencies` callers | Refactor preserves the public API signature; only adds an internal helper |

---

## Definition of Done

- [ ] `_extract_dependency_stems()` function exists and is covered by unit tests
- [ ] `extract_dependencies()` delegates to `_extract_dependency_stems()` — existing behavior unchanged
- [ ] `"structural_importance"` in `METADATA_KEYS`
- [ ] Pre-pass runs for `--mode code` and populates `file_ref_counts`
- [ ] Every code chunk carries `structural_importance` metadata
- [ ] MCP `_format_doc` shows importance when > 0
- [ ] MCP `_sync_multi_search` uses importance as distance tiebreaker
- [ ] All 13 new tests pass
- [ ] All existing tests pass (`pytest tests/` — 0 failures)
- [ ] `ingest.py` coverage ≥ 95%
