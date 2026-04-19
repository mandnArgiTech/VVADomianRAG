# STORY F: Chunk Min-Size Merging for Domain Doc Fragments

**Repository:** `mandnArgiTech/VVADomianRAG` branch `ngspice_rag`
**Priority:** Medium
**Estimated effort:** 2–3 hours
**Files to modify:** `ingest.py`
**Files to create:** `tests/test_chunk_min_merge.py`

---

## Business Context

The 176 ngspice domain doc chapters have a consistent structure: `# Title` → `## Introduction` → `## Mathematical Formulation` → `### subsections` → `## C Implementation` → `## Constants`. When `chunk_markdown_domain()` splits on `##` headers, short sections — a 2-line "Introduction" paragraph, a brief "### Implementation Constants" section listing 5 `#define` lines, or a table-of-contents stub — become tiny chunks (50–200 chars) that:

1. **Embed poorly** — embedding models need ~100+ tokens of semantic context to produce a meaningful vector. A 50-char chunk like `"## Implementation Constants\n\n#define DEFAULT_ABSTOL 1e-12"` gets a near-random embedding.
2. **Waste retrieval slots** — when Top-K is 10, a useless 50-char fragment occupies a slot that could hold the actual `DEVpnjlim` function implementation.
3. **Inflate ChromaDB storage** — thousands of tiny chunks across 176 chapters add embedding/storage overhead with zero retrieval value.

This story adds a **post-split merge pass** to `chunk_markdown_domain()` that combines adjacent chunks below a configurable minimum size threshold, preserving section hierarchy metadata from the first chunk in each merged group.

---

## Scope

1. A `_merge_small_chunks()` function that combines adjacent undersized chunks
2. Integrated into `chunk_markdown_domain()` as a post-processing step
3. Configurable via `CHUNK_MIN_SIZE` env var (default 500 chars)
4. Preserves section hierarchy metadata — merged chunk inherits the section breadcrumb from its first constituent
5. Also applies to `chunk_rfc()` since RFC docs have the same tiny-fragment problem

## Scope — What This Is NOT

- Not changing the primary `##`/`###` splitting logic
- Not modifying code chunking (AST chunks have natural function-level boundaries)
- Not a new Chroma collection or metadata field

---

## Acceptance Criteria

### AC-1: `_merge_small_chunks` function

**Given** a list of `(text, metadata)` chunk tuples from `chunk_markdown_domain()`,
**When** `_merge_small_chunks(chunks, min_size=500)` is called,
**Then**:
- Adjacent chunks where `len(text) < min_size` are merged with their next neighbor
- The merged chunk's text is `chunk_a_text + "\n\n" + chunk_b_text`
- The merged chunk's metadata inherits from the **first** chunk in the merge group, except:
  - `chunk_index` is renumbered sequentially (0, 1, 2, ...)
  - `section` is kept from the first chunk (preserves the broadest hierarchy context)
  - `chunk_type` is kept from the first chunk
- Merging stops growing a group when the accumulated text exceeds `max_size` (default: the `t_max` value from `_md_char_targets`, typically 5000 chars)
- A chunk that is already above `min_size` is never merged with anything

### AC-2: Merge respects section boundaries

**Given** chunks from two different `##` sections,
**When** both are below `min_size`,
**Then** they are **NOT** merged across section boundaries. A small "## Introduction" chunk stays with Introduction content; it does not merge with a "## Mathematical Formulation" chunk.

**Implementation:** Only merge adjacent chunks that share the same top-level `##` section (compare the first `>` segment of the `section` metadata field).

### AC-3: Integrated into `chunk_markdown_domain`

**Given** `chunk_markdown_domain()` in `ingest.py`,
**When** this story is complete,
**Then** the function calls `_merge_small_chunks(chunks, min_size, max_size)` before returning, where `min_size` defaults to `int(os.environ.get("CHUNK_MIN_SIZE", "500"))`.

### AC-4: Integrated into `chunk_rfc`

**Given** `chunk_rfc()` in `ingest.py`,
**When** this story is complete,
**Then** the same `_merge_small_chunks` post-pass is applied before returning.

### AC-5: Measurable chunk count reduction

**Given** the 176 ngspice domain doc chapters ingested with default settings,
**When** before this story vs after,
**Then** total chunk count is reduced by at least 20% (based on Open WebUI's documented 90% reduction for their similar feature — our reduction will be more modest because our primary split boundaries are already section-aware, but short sections within chapters will still benefit).

### AC-6: No chunk exceeds max_size after merging

**Given** any input document,
**When** `_merge_small_chunks` runs,
**Then** no output chunk has `len(text) > max_size`. The merge process stops growing a group at the max boundary.

### AC-7: All existing tests pass

`pytest tests/` — 0 failures, ≥ 95% coverage on `ingest.py`.

---

## Implementation Guide

### Step 1: `_merge_small_chunks` function

Add to `ingest.py` near `_split_paragraphs` (around line 993):

```python
def _merge_small_chunks(
    chunks: List[Tuple[str, Dict[str, str]]],
    min_size: int = 500,
    max_size: int = 5000,
) -> List[Tuple[str, Dict[str, str]]]:
    """Merge adjacent undersized chunks within the same top-level section.

    Inspired by Open WebUI's Chunk Min Size Target: tiny fragments after
    header-based splitting embed poorly and waste retrieval slots.
    """
    if not chunks or min_size <= 0:
        return chunks

    def _top_section(meta: Dict[str, str]) -> str:
        """Extract top-level section boundary key from chunk metadata.

        Domain doc chunks use ``section`` field with hierarchy like 'Title > Section > Sub'.
        RFC chunks use ``section_number`` and ``section_title`` instead.
        This function handles both schemas so _merge_small_chunks works for
        both chunk_markdown_domain() and chunk_rfc() output.
        """
        sec = (meta.get("section") or "").strip()
        if sec:
            parts = sec.split(" > ")
            # Return first two segments (doc title + ## heading) as boundary key
            return " > ".join(parts[:2]) if len(parts) >= 2 else sec
        # RFC fallback: use section_number (e.g., "3.2") → top-level "3"
        sec_num = (meta.get("section_number") or "").strip()
        if sec_num:
            return sec_num.split(".")[0]  # "3.2.1" → "3" (top-level RFC section)
        # Last resort: section_title
        return (meta.get("section_title") or "").strip()

    out: List[Tuple[str, Dict[str, str]]] = []
    buf_text = ""
    buf_meta: Optional[Dict[str, str]] = None
    buf_section = ""

    for text, meta in chunks:
        cur_section = _top_section(meta)

        # If buffer is empty, start a new group
        if not buf_text:
            buf_text = text
            buf_meta = dict(meta)
            buf_section = cur_section
            continue

        # Can we merge? Same section, buffer is small, merged wouldn't exceed max
        same_section = cur_section == buf_section
        buf_small = len(buf_text) < min_size
        merged_len = len(buf_text) + len(text) + 2  # +2 for "\n\n"
        fits = merged_len <= max_size

        if same_section and buf_small and fits:
            buf_text = buf_text + "\n\n" + text
            # Keep buf_meta from first chunk (AC-1)
        else:
            # Flush buffer
            out.append((buf_text, buf_meta))
            buf_text = text
            buf_meta = dict(meta)
            buf_section = cur_section

    # Flush final buffer
    if buf_text and buf_meta is not None:
        out.append((buf_text, buf_meta))

    # Renumber chunk_index sequentially (AC-1)
    for i, (text, meta) in enumerate(out):
        meta["chunk_index"] = str(i)

    return out
```

### Step 2: Wire into `chunk_markdown_domain`

At the end of `chunk_markdown_domain()`, before the `return chunks` line (around line 1319):

```python
    # --- Post-split merge of tiny fragments (Story F) ---
    min_sz = int(os.environ.get("CHUNK_MIN_SIZE", "500"))
    if min_sz > 0 and len(chunks) > 1:
        chunks = _merge_small_chunks(chunks, min_size=min_sz, max_size=t_max)

    return chunks
```

### Step 3: Wire into `chunk_rfc`

Same pattern at the end of `chunk_rfc()`, before its return statement (~line 1403 in `ingest.py`).

**Note:** The `chunk_rfc` return at line 1403 is tagged `# pragma: no cover`. The merge integration should be placed just before that return. For testing, use a **direct unit test** of `_merge_small_chunks` with RFC-style metadata (containing `section_number` and `section_title` instead of `section`) rather than an end-to-end `chunk_rfc` test.

**RFC metadata schema differs from domain docs:**
- Domain doc chunks: `section = "Title > Mathematical Formulation > Subsection"`
- RFC chunks: `section_number = "3.2"`, `section_title = "Header Compression"`

The `_top_section` helper (updated in Step 1 above) handles both schemas: it checks `section` first (domain docs), falls back to `section_number` for RFC chunks (extracting the top-level number, e.g., "3.2.1" → "3"), and finally falls back to `section_title`.

---

## Test Plan

### File: `tests/test_chunk_min_merge.py`

```
Test ID | Description | Approach
--------|-------------|----------
CM-01   | Small adjacent chunks in same section are merged | 3 chunks: 100, 80, 200 chars, all section "A". min_size=500. Assert 1 merged chunk
CM-02   | Large chunk is never merged | Chunks: 600, 100, 100 chars, section "A". min_size=500. Assert first chunk stays alone, latter two merge
CM-03   | Cross-section merge blocked | Chunk 100 chars section "A > Intro", chunk 100 chars section "A > Math". Assert 2 chunks remain (not merged)
CM-04   | Same section merge allowed | Chunk 100 chars section "A > Intro", chunk 100 chars section "A > Intro". Assert 1 merged chunk
CM-05   | Merged chunk does not exceed max_size | 10 chunks of 200 chars each, section "A". min_size=500, max_size=800. Assert multiple output chunks, none > 800
CM-06   | chunk_index renumbered after merge | 5 chunks merged to 3. Assert chunk_index values are "0", "1", "2"
CM-07   | Merged chunk inherits first chunk's section metadata | Chunks with section "Title > A" and "Title > A". Assert merged chunk has section "Title > A"
CM-08   | Empty input returns empty | Assert _merge_small_chunks([]) == []
CM-09   | min_size=0 disables merging | 3 small chunks. min_size=0. Assert 3 chunks returned unchanged
CM-10   | chunk_markdown_domain produces fewer chunks with merging | Feed Chapter_04_Newton_Raphson.md content. Count chunks without merge (CHUNK_MIN_SIZE=0) vs with (CHUNK_MIN_SIZE=500). Assert with < without
CM-11   | RFC metadata: _top_section extracts top-level from section_number | Chunk with section_number="3.2.1", no section field. Assert _top_section returns "3"
CM-12   | RFC adjacent chunks in same top-level section merge | Two chunks: section_number="3.1" and "3.2", both < min_size. Assert merged (both top-level "3")
CM-13   | Metadata fields other than chunk_index preserved | Merge two chunks with doc_title, source_c_files, device_family. Assert all preserved from first chunk
```

### Manual validation

```bash
# Without merging — count chunks
export CHUNK_MIN_SIZE=0
./run.sh --mode domain --domain spice --source ./Studio-Portable-RAG/DomainDocs/ngspice --dry-run 2>&1 | grep "chunks"

# With merging — count chunks
export CHUNK_MIN_SIZE=500
./run.sh --mode domain --domain spice --source ./Studio-Portable-RAG/DomainDocs/ngspice --dry-run 2>&1 | grep "chunks"
```

Expected: 20%+ reduction in chunk count with merging enabled.

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Merging loses section granularity | Merge is blocked across `##` section boundaries (AC-2). Only tiny fragments within the same section are combined. |
| Merged chunks too large for embedding model | `max_size` cap prevents exceeding the embedding model's token limit. Default aligned with `_md_char_targets`. |
| Existing ingest results change | This only affects future ingests. Existing ChromaDB data is untouched. A re-ingest of domain docs is needed to benefit. |
| Over-aggressive merging removes useful small chunks | `min_size=500` chars ≈ 125 tokens. Any chunk shorter than this genuinely has too little semantic content for a good embedding. Configurable via env var if needed. |

---

## Definition of Done

- [ ] `_merge_small_chunks()` function exists with section-boundary awareness
- [ ] `chunk_markdown_domain()` calls `_merge_small_chunks` before returning
- [ ] `chunk_rfc()` calls `_merge_small_chunks` before returning
- [ ] `CHUNK_MIN_SIZE` env var controls minimum threshold (default 500)
- [ ] No output chunk exceeds `max_size`
- [ ] `chunk_index` renumbered sequentially after merge
- [ ] Section metadata preserved from first chunk in merge group
- [ ] `_top_section` handles both domain doc (`section` field) and RFC (`section_number` field) metadata
- [ ] All 13 new tests pass, all existing tests pass, coverage ≥ 95%
