# STORY B: Call-Graph Metadata for Dependency-Aware Retrieval

**Repository:** `mandnArgiTech/VVADomianRAG` branch `ngspice_rag`
**Priority:** High
**Depends on:** Story A (structural_importance field must exist in METADATA_KEYS)
**Estimated effort:** 5–6 hours
**Files to modify:** `ingest.py`, `mcp_server.py`
**Files to create:** `tests/test_call_graph_metadata.py`

---

## Business Context

The NodalAI Python SPICE kernel (`ecad/mna_solver.py`, 4,810 lines) is being hardened against critical circuit benchmarks. When convergence fails on a real-world circuit (e.g., `Amplifier120W.cir`), the developer needs to understand:

1. **What does ngspice's `_nr_loop` equivalent (`NIiterate`) actually do?** — semantic search handles this.
2. **What functions does `NIiterate` call internally (`CKTload`, `SMPsolve`, `DEVload`)?** — semantic search CANNOT answer this because the callee functions live in different files with different vocabulary.

Today, VVADomianRAG stores a file-level `dependencies` field (which files does this file `#include`?) but has **zero call-level information** (which functions does this function body invoke?). This means when retrieving the ngspice chunk for `NIiterate`, the RAG cannot automatically pull in `CKTload`, `SMPsolve`, or `DEVload` — the developer has to manually ask for each one.

This story adds a **`calls`** metadata field to every C/C++ function chunk, listing the function names invoked within that function body. It then adds a **call-graph expansion** step in the MCP server: after retrieving the top-K chunks, the server automatically fetches chunks whose `chunk_name` matches any entry in the primary results' `calls` list.

### Why this matters for NodalAI specifically

The NodalAI `_nr_loop` (line 1696 of `ecad/mna_solver.py`) calls:
- `stamp_y_base` (linear stamp assembly)
- `_get_component_model` (device cache)
- `_limit_junction_voltage` (NR voltage clamp — the exact logic that needs to match ngspice)
- `evaluate_behavioral_dc` (behavioral source eval)
- `process_mosfet_model_params` (BSIM adapter)

When the developer asks "how does ngspice clamp junction voltages in NR iteration", the RAG retrieves the ngspice `NIiterate` chunk. With call-graph metadata, it ALSO automatically pulls in the ngspice `DEVload` and limiter chunks — exactly the context needed to fix NodalAI's `_limit_junction_voltage`.

---

## Scope — What This Story Is

1. Extract **called function names** from C function bodies using tree-sitter AST (not regex).
2. Store them in a new `calls` metadata field (pipe-delimited, like `concepts`).
3. Extract the same from Python function bodies during AST chunking.
4. Add a **call-graph expansion** phase in `mcp_server.py` that fetches callee chunks after primary search.

## Scope — What This Story Is NOT

- Not building a full call graph (caller→callee edges with weights). Just a flat list of callees per chunk.
- Not adding a new Chroma collection. Uses existing metadata fields + `chunk_name` matching.
- Not replacing `_sync_fetch_dependents` (file-level dependency expansion). This is a complementary **function-level** expansion that runs alongside it.

---

## Acceptance Criteria

### AC-1: C/C++ function call extraction via tree-sitter

**Given** a C function chunk extracted by `_ts_extract_chunks` in `ingest.py`,
**When** the chunk's tree-sitter node type is `function_definition`,
**Then** the chunk metadata includes a `calls` field containing a pipe-delimited list of function names called within that function body.

**Extraction rules:**
- Walk the function body subtree for `call_expression` nodes
- Extract the callee identifier (the function name being called)
- Skip standard library calls: ignore names matching `^(malloc|free|calloc|realloc|printf|fprintf|sprintf|snprintf|memcpy|memset|memmove|strlen|strcmp|strncmp|strcpy|strncpy|strcat|strncat|sizeof|abs|fabs|sqrt|log|exp|pow|ceil|floor|assert|exit|abort)$`
- Deduplicate, sort alphabetically, format as `|name1|name2|name3|` (same pipe-delimited convention as `concepts`)
- If no calls found, store empty string `""`

**Example:** For ngspice's `B1accept` function that calls `CKTload`, `SMPpreOrder`, and `NIdestroy`:
```
calls: |CKTload|NIdestroy|SMPpreOrder|
```

### AC-2: Python function call extraction via AST

**Given** a Python function chunk extracted by `ast_chunk_python` in `ingest.py`,
**When** the chunk node is a `FunctionDef` or `AsyncFunctionDef`,
**Then** the chunk metadata includes a `calls` field containing pipe-delimited function/method names invoked in the body.

**Extraction rules:**
- Walk the function AST for `ast.Call` nodes
- For `ast.Name` callees: use `node.func.id` (e.g., `np.zeros` → skip, `_sanitize_dc_linear_system` → include)
- For `ast.Attribute` callees: use `node.func.attr` (e.g., `self._nr_loop` → `_nr_loop`, `solver.solve_dc_op` → `solve_dc_op`)
- Skip builtins: `^(print|len|range|int|float|str|bool|list|dict|set|tuple|type|isinstance|issubclass|getattr|setattr|hasattr|super|enumerate|zip|map|filter|sorted|reversed|min|max|sum|any|all|abs|round|open|iter|next|hash|id|repr|format|vars|dir|property|staticmethod|classmethod)$`
- Deduplicate, sort, pipe-delimit

### AC-3: `calls` field in METADATA_KEYS

**Given** `METADATA_KEYS` in `ingest.py`,
**When** this story is complete,
**Then** `"calls"` appears in `METADATA_KEYS` after `"structural_importance"`

### AC-4: Non-function chunks get empty calls

**Given** a chunk whose type is `struct_specifier`, `enum_specifier`, `preproc_def`, `declaration`, `file_preamble`, or any non-function type,
**When** metadata is assembled,
**Then** `calls` is `""` (empty string)

### AC-5: MCP call-graph expansion

**Given** `mcp_server.py` function `_sync_multi_search`,
**When** primary search returns chunks that have non-empty `calls` metadata,
**Then** a **call-graph expansion** phase runs:

1. Collect all unique callee names from the `calls` fields of the top-K primary results
2. For each callee name, query Chroma with `where={"chunk_name": callee_name}` across code collections
3. Deduplicate against already-retrieved chunk IDs
4. Append matched callee chunks to the result set, marked with a distinct source type `"callee"` (so the LLM and developer can see these are dependency-expanded results)
5. Limit callee expansion to **max 10 additional chunks** total (configurable via environment variable `RAG_CALLEE_EXPAND_MAX`, default 10)
6. Callee chunks appear AFTER primary results in the formatted output, under a `## Called functions (auto-expanded)` header

### AC-6: Expansion is opt-in and backward compatible

**Given** the environment variable `RAG_CALLEE_EXPAND` is not set or is `"0"`,
**When** MCP search runs,
**Then** call-graph expansion is skipped entirely. Default is `"1"` (enabled).

### AC-7: Existing tests still pass

**Given** `pytest tests/`,
**When** run after this change,
**Then** all existing tests pass. Coverage ≥ 95% on `ingest.py`.

---

## Implementation Guide

### Step 1: C call extraction helper

**File:** `ingest.py`

Add a new function near `_ts_extract_chunks` (around line 1740):

```python
# Stdlib/runtime names to skip in call extraction (C/C++)
_C_STDLIB_CALLS: frozenset = frozenset({
    "malloc", "free", "calloc", "realloc",
    "printf", "fprintf", "sprintf", "snprintf", "vprintf", "vfprintf",
    "memcpy", "memset", "memmove", "memcmp",
    "strlen", "strcmp", "strncmp", "strcpy", "strncpy", "strcat", "strncat",
    "sizeof", "abs", "fabs", "sqrt", "log", "exp", "pow", "ceil", "floor",
    "assert", "exit", "abort", "perror", "strerror",
    "fopen", "fclose", "fread", "fwrite", "fseek", "ftell",
    "atoi", "atof", "strtol", "strtod",
})


def _extract_c_calls_from_node(node, content: str) -> List[str]:
    """Extract function call identifiers from a tree-sitter C function_definition node."""
    calls: set = set()

    def _walk_calls(n):
        if n.type == "call_expression":
            # First child is usually the function name (identifier or field_expression)
            func_node = n.children[0] if n.children else None
            if func_node is not None:
                if func_node.type == "identifier":
                    name = content[func_node.start_byte:func_node.end_byte]
                    if name not in _C_STDLIB_CALLS and not name.startswith("__"):
                        calls.add(name)
                elif func_node.type == "field_expression":
                    # e.g., obj->method — extract method name (last identifier)
                    for ch in reversed(func_node.children):
                        if ch.type == "field_identifier":
                            name = content[ch.start_byte:ch.end_byte]
                            if name not in _C_STDLIB_CALLS:
                                calls.add(name)
                            break
        for ch in n.children:
            _walk_calls(ch)

    # Walk only the function body (compound_statement), not the signature
    for child in node.children:
        if child.type == "compound_statement":
            _walk_calls(child)
            break

    return sorted(calls)
```

### Step 2: Wire into `_ts_extract_chunks`

**File:** `ingest.py`, inside `_ts_extract_chunks`, around line 1848–1873

In the block where chunk metadata is assembled (the `out.append(...)` call), add:

```python
# Extract calls for function chunks
calls_list: List[str] = []
if grammar == "c" and t == "function_definition":
    calls_list = _extract_c_calls_from_node(node, content)

# ... existing metadata assembly ...
out.append(
    (
        txt[:100000],
        {
            "chunk_strategy": f"ast_{grammar}",
            "chunk_type": chunk_type,
            "chunk_name": chunk_name[:200],
            "chunk_index": str(len(out)),
            "device_family": device_family_val,
            "calls": format_concepts_field(calls_list) if calls_list else "",
        },
    )
)
```

**Note:** Reuse `format_concepts_field` since calls use the same `|name1|name2|` convention.

### Step 3: Python call extraction in `ast_chunk_python`

**File:** `ingest.py`, inside `ast_chunk_python` (starts around line 1699)

The existing function extracts Python chunks using `ast.parse`. After extracting a `FunctionDef` or `AsyncFunctionDef` node, walk its body for `ast.Call` nodes:

```python
_PY_BUILTIN_CALLS: frozenset = frozenset({
    "print", "len", "range", "int", "float", "str", "bool",
    "list", "dict", "set", "tuple", "type", "isinstance", "issubclass",
    "getattr", "setattr", "hasattr", "super", "enumerate", "zip",
    "map", "filter", "sorted", "reversed", "min", "max", "sum",
    "any", "all", "abs", "round", "open", "iter", "next",
    "hash", "id", "repr", "format", "vars", "dir",
    "property", "staticmethod", "classmethod",
})


def _extract_py_calls(func_node: ast.AST) -> List[str]:
    """Extract called function/method names from a Python FunctionDef body."""
    calls: set = set()
    for node in ast.walk(func_node):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                name = node.func.id
                if name not in _PY_BUILTIN_CALLS and not name.startswith("_") == False:
                    calls.add(name)
            elif isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)
    # Remove builtins that leaked through attribute access
    calls -= _PY_BUILTIN_CALLS
    return sorted(calls)
```

Wire this into the chunk metadata assembly for Python function chunks.

### Step 4: Add `calls` to METADATA_KEYS

**File:** `ingest.py`, line 182

Add `"calls"` after `"structural_importance"` (added in Story A) or after `"device_family"` if Story A is not yet merged.

### Step 5: MCP call-graph expansion

**File:** `mcp_server.py`

Add a new function after `_sync_fetch_dependents` (~line 695):

```python
RAG_CALLEE_EXPAND = os.environ.get("RAG_CALLEE_EXPAND", "1").strip()
RAG_CALLEE_EXPAND_MAX = int(os.environ.get("RAG_CALLEE_EXPAND_MAX", "10"))


def _sync_fetch_callees(
    primary: List[Tuple[Any, Optional[float], str]],
    cmap: Dict[str, Chroma],
    search_type: str,
    domain: str,
    max_callees: int = RAG_CALLEE_EXPAND_MAX,
) -> List[Tuple[Any, Optional[float], str]]:
    """Fetch chunks whose chunk_name matches callees from primary results' `calls` metadata."""
    if RAG_CALLEE_EXPAND not in ("1", "true", "yes"):
        return []

    # 1. Collect callee names from primary results
    callee_names: set = set()
    seen_ids: set = set()
    for doc, dist, stype in primary:
        meta = getattr(doc, "metadata", None) or {}
        seen_ids.add(getattr(doc, "id", None) or id(doc))
        calls_raw = (meta.get("calls") or "").strip()
        if calls_raw.startswith("|"):
            for name in calls_raw.strip("|").split("|"):
                name = name.strip()
                if name:
                    callee_names.add(name)

    if not callee_names:
        return []

    # 2. Query Chroma for matching chunk_name
    targets = _select_collection_names(cmap, search_type, domain)
    out: List[Tuple[Any, Optional[float], str]] = []

    for callee in sorted(callee_names):
        if len(out) >= max_callees:
            break
        for coll_name in targets:
            if len(out) >= max_callees:
                break
            vs = cmap[coll_name]
            col = getattr(vs, "_collection", None)
            if col is None:
                continue
            try:
                res = col.get(
                    where={"chunk_name": {"$eq": callee}},
                    limit=2,
                    include=["documents", "metadatas", "ids"],
                )
            except Exception:
                continue
            for i, did in enumerate(res.get("ids") or []):
                if did in seen_ids or len(out) >= max_callees:
                    continue
                seen_ids.add(did)
                meta = (res.get("metadatas") or [{}])[i] if i < len(res.get("metadatas") or []) else {}
                text = (res.get("documents") or [""])[i] if i < len(res.get("documents") or []) else ""
                doc = Document(page_content=text, metadata=dict(meta or {}))
                out.append((doc, None, "callee"))

    return out
```

### Step 6: Integrate into search_knowledge tool

**File:** `mcp_server.py`, inside the `search_knowledge` tool handler

After the existing `_sync_fetch_dependents` call (which adds file-level dependent chunks), add:

```python
# Call-graph expansion: fetch callee function chunks
callee_hits = _sync_fetch_callees(primary_results, cmap, search_type, domain)
if callee_hits:
    text += "\n\n## Called functions (auto-expanded)\n\n"
    for doc, dist, stype in callee_hits:
        text += _format_doc(doc, dist) + "\n\n"
```

---

## Test Plan

### File: `tests/test_call_graph_metadata.py`

```
Test ID | Description | Approach
--------|-------------|----------
CG-01   | _extract_c_calls_from_node extracts simple calls | Parse C code: `void foo() { bar(); baz(); }` with tree-sitter. Assert calls == ["bar", "baz"]
CG-02   | C extraction skips stdlib calls | Parse: `void foo() { malloc(10); CKTload(ckt); free(p); }`. Assert calls == ["CKTload"]
CG-03   | C extraction handles field_expression (ptr->method) | Parse: `void foo() { ckt->CKTload(ckt); }`. Assert "CKTload" in calls
CG-04   | C extraction returns empty for no-call function | Parse: `int answer() { return 42; }`. Assert calls == []
CG-05   | C extraction handles nested calls | Parse: `void foo() { alpha(beta(gamma())); }`. Assert calls == ["alpha", "beta", "gamma"]
CG-06   | C extraction skips macro-like uppercase only if in stdlib set | Parse: `void foo() { TMALLOC(p, 10); DEVload(dev); }`. Assert "TMALLOC" and "DEVload" both present (neither is in stdlib set)
CG-07   | Python _extract_py_calls extracts function calls | Parse: `def foo():\n    bar()\n    baz.qux()`. Assert calls includes "bar" and "qux"
CG-08   | Python extraction skips builtins | Parse: `def foo():\n    x = len(items)\n    process(x)`. Assert calls == ["process"]
CG-09   | Python extraction handles self.method() | Parse: `def foo(self):\n    self._nr_loop()\n    self.solve()`. Assert calls == ["_nr_loop", "solve"]
CG-10   | "calls" in METADATA_KEYS | `assert "calls" in METADATA_KEYS`
CG-11   | Function chunks get calls metadata | Mock ingest of a C file with one function that calls 3 others. Assert chunk metadata["calls"] == "|callee1|callee2|callee3|"
CG-12   | Struct chunks get empty calls | Mock ingest of a C file with a struct_specifier. Assert chunk metadata["calls"] == ""
CG-13   | MCP _sync_fetch_callees finds callee chunks | Set up mock Chroma with chunk_name="CKTload". Create primary result with calls="|CKTload|SMPsolve|". Assert _sync_fetch_callees returns the CKTload chunk
CG-14   | MCP expansion respects max_callees limit | Primary has calls with 20 unique names, all present in Chroma. Set max_callees=5. Assert len(result) == 5
CG-15   | MCP expansion deduplicates against primary | Primary already contains chunk with chunk_name="CKTload". Primary also has calls="|CKTload|". Assert expansion does NOT re-add CKTload
CG-16   | MCP expansion disabled when RAG_CALLEE_EXPAND=0 | Set env var to "0". Assert _sync_fetch_callees returns []
CG-17   | Pipe-delimited calls field round-trips through format_concepts_field | calls=["alpha", "beta"]. Assert format_concepts_field(calls) == "|alpha|beta|". Assert iter_concept_ids("|alpha|beta|") == ["alpha", "beta"]
```

### Running tests

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest tests/test_call_graph_metadata.py -v
```

### Manual validation — ngspice C source

After implementation, ingest the ngspice source:

```bash
./run.sh --mode code --domain spice --source /path/to/ngspice/src
```

Query for Newton-Raphson iteration:

```bash
./query.sh semantic "Newton-Raphson iteration convergence loop" --domain spice
```

**Expected behavior:**
- Primary results include `NIiterate` or equivalent NR loop function
- `calls` metadata on that chunk includes names like `CKTload`, `SMPsolve`, `DEVload`
- Callee expansion automatically includes the `CKTload` and `DEVload` function chunks below a `## Called functions (auto-expanded)` header
- The developer now sees both the NR loop AND the device load functions in a single retrieval

### Manual validation — NodalAI Python source

Ingest the NodalAI ecad package:

```bash
./run.sh --mode code --domain spice --source /path/to/NodalAI/ecad
```

Query:

```bash
./query.sh semantic "DC operating point solve" --domain spice
```

**Expected behavior:**
- Primary result is `solve_dc_op` or `_solve_dc_op_core`
- `calls` metadata includes `_nr_loop`, `_gmin_stepping`, `_source_stepping`, `_pseudotransient_continuation`
- Callee expansion pulls in `_nr_loop` chunk (the most critical function for convergence debugging)

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Tree-sitter `call_expression` misses macro-wrapped calls like `TMALLOC(...)` | In tree-sitter C grammar, macros that look like function calls ARE parsed as `call_expression`. Verified: `TMALLOC(ptr, 10)` produces a call_expression node with identifier `TMALLOC`. |
| Call list is too long for deeply nested functions (bloats metadata) | Cap at 50 unique callees per chunk. Beyond 50, truncate and append `__truncated__` sentinel. |
| `chunk_name` matching in Chroma is exact-match only | This is correct behavior. `chunk_name` in `_ts_extract_chunks` is set to the function identifier (line 1797). Exact match is what we want. |
| Callee expansion adds latency to every MCP query | Expansion only runs when primary results have non-empty `calls`. For domain-doc or RFC queries, `calls` is always empty — zero overhead. For code queries, the Chroma `get(where=...)` calls are fast (metadata index, no embedding computation). |
| Python AST extraction misses dynamic calls (`getattr(obj, method_name)()`) | Accepted limitation. Dynamic dispatch is rare in NodalAI's kernel code. The AST covers 95%+ of actual calls. |
| Callee names collide across files (e.g., multiple `init` functions) | `chunk_name` match returns multiple chunks; all are included up to the max limit. The developer sees all candidates — this is acceptable and even helpful for cross-referencing. |

---

## Cross-Reference: How This Helps NodalAI Hardening

| NodalAI bug pattern | Without call-graph | With call-graph |
|---------------------|-------------------|-----------------|
| `_nr_loop` convergence failure on BJT differential pair | RAG returns ngspice NR loop chunk only. Developer must manually search for `DEVload`, `BJTload` | RAG returns NR loop + auto-expands `DEVload` and `BJTload` chunks. Developer sees the full Newton-Raphson + device stamp pipeline. |
| MOSFET `_limit_junction_voltage` doesn't match ngspice behavior | RAG returns nodalai's `_limit_junction_voltage` and ngspice's limiter separately. No connection. | RAG shows ngspice's `NIiterate` calls `DEVload` which calls `BSIM4limit`. Full chain visible. |
| `solve_transient` timestep rejection logic differs from ngspice | RAG returns transient solve chunk. Callee `_nr_loop`, `_eval_source_pre`, `_next_breakpoint_pre` auto-expanded. | Same query on ngspice returns `DCTran` + callees `NIiter`, `CKTtrunc`, `SPfrontEnd`. Direct function-level comparison enabled. |

---

## Definition of Done

- [ ] `_extract_c_calls_from_node()` function exists and handles simple, nested, and field-expression calls
- [ ] `_extract_py_calls()` function exists and handles Name, Attribute, and self.method() calls
- [ ] `_C_STDLIB_CALLS` and `_PY_BUILTIN_CALLS` frozensets are defined
- [ ] `"calls"` in `METADATA_KEYS`
- [ ] C function chunks carry `calls` metadata (pipe-delimited)
- [ ] Python function chunks carry `calls` metadata (pipe-delimited)
- [ ] Non-function chunks have empty `calls`
- [ ] MCP `_sync_fetch_callees` function exists and is gated by `RAG_CALLEE_EXPAND` env var
- [ ] `search_knowledge` output includes `## Called functions (auto-expanded)` section when callees are found
- [ ] All 17 new tests pass
- [ ] All existing tests pass (`pytest tests/` — 0 failures)
- [ ] `ingest.py` coverage ≥ 95%
