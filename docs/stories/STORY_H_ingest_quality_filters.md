# STORY H: Ingest Quality — Exclude Frontend Noise, Filter Tiny Code Chunks, Fix God Mode False Positives

**Repository:** `mandnArgiTech/VVADomianRAG` branch `ngspice_rag`
**Priority:** High
**Estimated effort:** 3–4 hours
**Files to modify:** `ingest.py`, `query.py`, `mcp_server.py`
**Files to create:** `tests/test_ingest_quality_filters.py`

---

## Business Context

Raw retrieval testing revealed that ~25 out of ~30 result chunks are noise when querying for diode voltage limiting. Three root causes identified:

### Problem 1: `frontend/terminal.c` floods results

The ngspice `src/frontend/` directory (terminal UI, X11 graphics, misc utilities) was ingested into `spice_code`. Every declaration in `terminal.c` (`static char *motion_chars;`, `char tbuf[1025];`, `void term_clear(void);`) becomes a separate chunk with `chunk_name: "terminal"`. These are completely irrelevant to circuit simulation but consume retrieval slots.

**The gitignore mechanism exists** (`--write-ngspice-gitignore` adds `src/frontend/` to `.gitignore`) but must be run BEFORE ingest. If the user forgot, or if the `.gitignore` wasn't present during the original ingest, the frontend code is already in ChromaDB.

### Problem 2: One-line declaration chunks pollute the index

Tree-sitter AST extraction creates individual chunks for every C declaration: `static char *motion_chars;` (32 chars), `double daddb2;` (15 chars), `#define VERTICAL 1` (20 chars). These embed poorly (too short for meaningful vectors) and waste retrieval slots. The chunk min-size merge (Story F) only applies to markdown domain docs, not code chunks.

### Problem 3: God mode false-matches `terminal` from vocab

The `symbols_vocabulary.json` likely contains `"terminal"` (from `terminal.c` / `terminal.h`). God mode's token matching extracts tokens from the query using `re.findall(r'[\w\.]+', query)` and matches them against the vocab. Since God mode results get distance 0.0000 and are prepended before all other results, a single false vocab match dumps 15+ irrelevant chunks at the top.

The root cause: God mode doesn't distinguish between a 2000-line function named `DIOload` (high-value match) and a one-line declaration `char *s;` from a file stem `terminal` (noise). Every chunk from the matched file gets returned.

---

## Acceptance Criteria

### AC-1: Code chunk minimum size filter during ingest

**Given** tree-sitter AST extraction produces chunks of varying sizes,
**When** a code chunk has `len(text) < CODE_CHUNK_MIN_SIZE` (default 50 chars),
**Then** it is **dropped** from the chunk list before embedding and upsert.

This filters out:
- Single-line declarations: `static char *motion_chars;` (32 chars)
- Trivial preprocessor defines: `#define VERTICAL 1` (20 chars)
- Empty struct specifiers: `struct winsize` (15 chars)
- One-line function declarations in headers: `void term_clear(void);` (22 chars)

This does NOT filter out:
- Full function definitions (always >50 chars)
- Multi-field struct definitions (always >50 chars)
- Preprocessor defines with actual values: `#define GMIN ckt->CKTgmin` (keeps ngspice constants)
- File preamble chunks (copyright blocks, always >50 chars)

Configurable via `CODE_CHUNK_MIN_SIZE` env var. Set to `0` to disable.

### AC-2: Expanded ngspice gitignore entries

**Given** `_NGSPICE_GITIGNORE_ENTRIES` in `ingest.py`,
**When** this story is complete,
**Then** the list includes additional noise directories:

```python
_NGSPICE_GITIGNORE_ENTRIES = [
    "src/frontend/",
    "src/x11/",
    "src/misc/",
    "src/compat/",
    "src/spicelib/devices/hisim*",
    "src/spicelib/devices/soi*",
    # New additions:
    "src/spicelib/devices/adms/",      # Verilog-A auto-generated, not hand-written C
    "src/spicelib/devices/numd*",      # Numerical device (CIDER) - rarely needed
    "src/spicelib/devices/nbjt*",      # Numerical BJT (CIDER)
    "src/spicelib/devices/numos*",     # Numerical MOS (CIDER)
    "src/ciderlib/",                   # CIDER numerical library
    "tests/",                          # ngspice test suite - not reference code
    "*.txt",                           # ngspice.txt manual dump (huge, low-value text)
]
```

**Note:** Only add entries that are genuinely noise for circuit simulation debugging. The CIDER entries are optional — include them if the user hasn't specifically asked for numerical device support. The `adms/` directory contains auto-generated Verilog-A wrappers that aren't useful as reference implementations.

### AC-3: God mode filters out tiny chunks

**Given** `_exact_chunk_name_results` in `mcp_server.py` and `query.py`,
**When** God mode retrieves chunks by `chunk_name`,
**Then** chunks with `len(page_content) < 50` are excluded from the results.

This prevents one-line declarations from `terminal.c` (matched via file-stem `chunk_name: "terminal"`) from flooding the top results.

### AC-4: God mode excludes known-noise file stems

**Given** God mode's token matching,
**When** a query token matches a vocab entry that is a known-noise file stem,
**Then** the match is skipped.

Add a denylist:

```python
_GOD_MODE_STEM_DENYLIST = frozenset({
    "terminal", "main", "init", "util", "utils", "helper", "helpers",
    "common", "config", "test", "tests", "setup", "build", "makefile",
    "readme", "changelog", "license", "todo", "fixme",
})
```

When God mode finds a vocab match that is also in this denylist AND the query does not contain the exact full filename (e.g., `terminal.c`), skip the match.

### AC-5: Existing chunks can be purged by source path prefix

**Given** `frontend/terminal.c` chunks are already in ChromaDB from a previous ingest,
**When** the user runs:
```bash
./run.sh --mode code --domain spice --source /path/to/ngspice/src --purge-prefix src/frontend
```
**Then** all chunks with `source` metadata containing the prefix are deleted from the collection before re-ingest begins.

If `--purge-prefix` is too complex for this story, at minimum document the manual cleanup:
```python
# Manual ChromaDB cleanup
import chromadb
client = chromadb.PersistentClient(path="./Studio-Portable-RAG/VectorDB")
coll = client.get_collection("spice_code")
# Delete all chunks from frontend/
results = coll.get(where={"relative_path": {"$contains": "frontend/"}}, include=[])
if results["ids"]:
    coll.delete(ids=results["ids"])
```

### AC-6: All existing tests pass

`pytest tests/` — 0 failures.

---

## Implementation Guide

### Step 1: Code chunk minimum size filter

**File:** `ingest.py`

In `_ts_extract_chunks` (the tree-sitter extraction function), after the chunks are assembled in the `out` list but before returning, add a filter:

```python
# Filter tiny code chunks that embed poorly (Story H, AC-1)
code_min = int(os.environ.get("CODE_CHUNK_MIN_SIZE", "50"))
if code_min > 0:
    out = [(text, meta) for text, meta in out if len(text.strip()) >= code_min]
```

Apply the same filter in `_ts_extract_chunks_or_language_split_c_cpp` and `_ts_extract_chunks_or_language_split_java` — anywhere that produces code chunks.

**Exception:** Do NOT filter `file_preamble` chunks — they carry copyright/author info that's useful for attribution even if short.

```python
out = [
    (text, meta) for text, meta in out
    if len(text.strip()) >= code_min or meta.get("chunk_type") == "file_preamble"
]
```

### Step 2: Expand gitignore entries

**File:** `ingest.py`, `_NGSPICE_GITIGNORE_ENTRIES`

Add the entries from AC-2.

### Step 3: God mode tiny-chunk filter

**File:** `mcp_server.py` in `_exact_chunk_name_results`, and `query.py` in the equivalent function.

After retrieving chunks by `chunk_name`, filter:

```python
# Filter tiny chunks from God mode results (Story H, AC-3)
GOD_MODE_MIN_CONTENT_SIZE = 50
# ... inside the results loop:
text = (res.get("documents") or [""])[i]
if len((text or "").strip()) < GOD_MODE_MIN_CONTENT_SIZE:
    continue
```

### Step 4: God mode stem denylist

**File:** `query.py` in `_god_mode_chunk_name_matches`

Before adding a vocab match to the output list, check against the denylist:

```python
_GOD_MODE_STEM_DENYLIST = frozenset({
    "terminal", "main", "init", "util", "utils", "helper", "helpers",
    "common", "config", "test", "tests", "setup", "build",
})

# Inside the matching loop:
for t in tokens:
    if t in vocab:
        if t.lower() not in _GOD_MODE_STEM_DENYLIST:
            add(t)
        continue
    c = canon_lower.get(t.lower())
    if c and c.lower() not in _GOD_MODE_STEM_DENYLIST:
        add(c)
```

### Step 5: Document manual cleanup

Add to `README.md` or `RUN_SH_USER_GUIDE.md` the ChromaDB cleanup snippet from AC-5.

---

## Test Plan

### File: `tests/test_ingest_quality_filters.py`

```
Test ID | Description | Approach
--------|-------------|----------
IQ-01   | Code chunks < 50 chars filtered out | Mock _ts_extract_chunks output with 3 chunks: 20, 60, 200 chars. Assert only 60 and 200 survive
IQ-02   | file_preamble chunks preserved even if short | Mock chunk with type="file_preamble", 30 chars. Assert it survives the filter
IQ-03   | CODE_CHUNK_MIN_SIZE=0 disables filter | Set env var to "0". Assert all chunks pass through
IQ-04   | CODE_CHUNK_MIN_SIZE=100 raises threshold | Set env var to "100". Assert 60-char chunk is now filtered
IQ-05   | Expanded gitignore includes adms and ciderlib | Assert "src/spicelib/devices/adms/" in _NGSPICE_GITIGNORE_ENTRIES
IQ-06   | God mode filters chunks < 50 chars | Mock Chroma get() returning 3 chunks: 10, 60, 200 chars. Assert only 60 and 200 in results
IQ-07   | God mode denylist blocks "terminal" | Query "thermal voltage terminal". Assert "terminal" NOT in God mode matches
IQ-08   | God mode denylist does NOT block "DIOload" | Query "DIOload thermal". Assert "DIOload" IS in God mode matches
IQ-09   | God mode denylist allows "terminal" if exact filename in query | Query "terminal.c thermal". Assert "terminal" IS in matches (user explicitly asked for it)
IQ-10   | Denylist is case-insensitive | Query with "Terminal". Assert still blocked
IQ-11   | After filter, chunk_index still valid | Filter 5 chunks to 3. Assert metadata chunk_index values are sequential
IQ-12   | Filter applies to C, C++, and Java chunks | Test with grammar="c", "cpp", "java". Assert filter runs for all three
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Filtering drops useful short chunks like `#define GMIN ckt->CKTgmin` (36 chars) | 50-char threshold is conservative. This specific define is 36 chars and would be filtered. Raise concern: consider 30 instead of 50, or exempt `core_constant` chunk_type like we exempt `file_preamble`. |
| God mode denylist blocks legitimate queries about "terminal" emulation | Denylist only blocks when the token appears as a vocab match, not when it's in the semantic query. And AC-4 says if the user types the full filename `terminal.c`, the match is allowed. |
| Expanded gitignore removes CIDER code that someone might need | CIDER entries are clearly marked as optional. User can remove them from the list before ingesting. |
| Purging existing chunks requires manual ChromaDB commands | Documented in README. A `--purge-prefix` flag would be better but is lower priority. |

---

## Impact Estimate

For a query like "DIOload DEVpnjlim junction voltage clamp":
- **Before:** ~5 useful chunks + ~25 noise chunks (terminal.c declarations, JFET2 macros, ngspice.txt text dump)
- **After:** ~5 useful chunks + ~3 low-relevance-but-not-noise chunks (e.g., HICUM depletion charge — semantically related even if not the primary answer)

The signal-to-noise ratio goes from ~17% to ~60%.

---

## Definition of Done

- [ ] Code chunks < `CODE_CHUNK_MIN_SIZE` (default 50) filtered during AST extraction
- [ ] `file_preamble` and `core_constant` chunks exempt from size filter
- [ ] `_NGSPICE_GITIGNORE_ENTRIES` expanded with adms, ciderlib, tests, *.txt
- [ ] God mode filters chunks with `len(content) < 50`
- [ ] God mode `_GOD_MODE_STEM_DENYLIST` blocks common noise stems
- [ ] Manual ChromaDB cleanup documented
- [ ] All 12 new tests pass, all existing tests pass
