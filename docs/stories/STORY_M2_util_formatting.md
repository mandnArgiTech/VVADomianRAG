# STORY M2 — util/formatting.py

**Branch:** `ngspice_rag`  
**Status:** Done (verified)  
**Depends on:** M1 (util/constants.py must exist first)

---

## Context

`_infer_source_type`, `_fence_for`, `_truncate_chunk`, and `format_result`
are copy-pasted in both `query.py` and `mcp_server.py`.  `format_result`
has **diverged** — `mcp_server.py` has two extra source-type branches
(`callee` and enriched `domain_doc`) plus `_structural_importance_int`.

This story merges them into one authoritative `util/formatting.py`.

---

## M2-A  Create `util/formatting.py`

### Imports

```python
"""util/formatting.py — Result and chunk formatting for VVADomainRAG."""
from __future__ import annotations
import os
from typing import Any, Callable, Dict, List, Optional
from util.constants import LANG_TAG, RESULT_CHUNK_MAX_CHARS, RESULT_CONTEXT_WINDOW_MAX_CHARS
```

### `infer_source_type`

Copy **verbatim** from `query.py` (both versions are identical — 20 lines).

### `fence_for`

Copy **verbatim** from `query.py` (both versions identical — 2 lines).

### `truncate_chunk`

The two versions differ only in the truncation label string:
- `query.py` uses `"... (truncated for response size) ..."`
- `mcp_server.py` uses `"... (truncated for MCP response size) ..."`

Use the neutral label `"... (truncated) ..."` in the util version.
Copy the rest of the body verbatim from `query.py`.

Signature:
```python
def truncate_chunk(text: str, max_chars: Optional[int] = None) -> str:
```

### `format_result` — merged version

This is the critical function.  Build the merged version as follows:

**Signature** (unchanged from both callers — do NOT add extra parameters):
```python
def format_result(doc: Any, score: Optional[float], source_type: str) -> str:
```

**Body** — merge the two implementations:

1. Copy the preamble (meta extraction, header list, cw/content selection,
   ext extraction) verbatim from either file — they are identical.

2. Add the `callee` branch from **`mcp_server.py`** FIRST (it is absent from
   `query.py`):
```python
if source_type == "callee":
    if repo:
        header.append(f"**Repo:** {repo}")
    header.append(f"**File:** {repo + '/' + src if repo else src}")
    if cname:
        header.append(f"**Component:** {cname} ({ctype})")
    # structural_importance — read directly from metadata (avoids importing mcp helper)
    si = int(meta.get("structural_importance", 0) or 0)
    if si > 0:
        header.append(f"**importance:** {si}")
    lang = LANG_TAG.get(ext, "")
    fence = fence_for(content)
    return "### Callee (auto-expanded)\n" + "\n".join(header) + f"\n\n{fence}{lang}\n{content}\n{fence}"
```

3. The `code` branch — merge from both:
   - From `query.py`: `calls` field rendering using `_metadata_pipe_or_comma_tokens`
   - From `mcp_server.py`: `structural_importance` field, `iter_concept_ids` for calls splitting

   Use this merged `code` branch:
```python
if source_type == "code":
    if repo:
        header.append(f"**Repo:** {repo}")
    header.append(f"**File:** {repo + '/' + src if repo else src}")
    if cname:
        header.append(f"**Component:** {cname} ({ctype})")
    si = int(meta.get("structural_importance", 0) or 0)
    if si > 0:
        header.append(f"**importance:** {si}")
    dep = (meta.get("dependencies") or "").strip()
    if dep:
        dshow = dep if len(dep) <= 500 else dep[:500] + "…"
        header.append(f"**dependencies:** {dshow}")
    calls_str = (meta.get("calls") or "").strip()
    if calls_str:
        # split pipe-or-comma field
        s = calls_str.strip("|")
        raw_calls = [x.strip() for x in s.split("|") if x.strip()] if "|" in calls_str \
                    else [x.strip() for x in calls_str.split(",") if x.strip()]
        callees_list = [c for c in raw_calls if c != "__truncated__"][:15]
        if callees_list:
            header.append(f"**Callees (Outgoing):** {', '.join(callees_list)}")
    if meta.get("retrieval_hop") == "caller":
        header.append("**[CALLER NODE]** This chunk calls the primary retrieved function.")
    lang = LANG_TAG.get(ext, "")
    fence = fence_for(content)
    return "### Code\n" + "\n".join(header) + f"\n\n{fence}{lang}\n{content}\n{fence}"
```

4. The `domain_doc / theory / wiki` branch — use the **`mcp_server.py` version**
   (it includes the `source_c_files` related-files block that `query.py` lacks):
```python
if source_type in ("domain_doc", "theory", "wiki"):
    sec = meta.get("section", meta.get("doc_title", "Domain Knowledge"))
    src_files = (meta.get("source_c_files") or "").strip()
    rel_block = ""
    if src_files:
        rel_block = "\n\n## Related source files\n\n" + ", ".join(
            x.strip() for x in src_files.split(",") if x.strip()
        )
    return f"### {sec}\n*Source: {meta.get('source', '')}*{rel_block}\n\n{content}"
```

5. Remaining branches (`rfc`, `rally`/`customer`, `mib`, `community`, fallback)
   — copy verbatim from either file (they are identical).

### Output formatters

Copy these four functions **verbatim** from `query.py`:

```python
def format_markdown(hits: List[Any], query: str) -> str: ...
def format_concept_markdown(hits: List[Any], concept: str) -> str: ...
def format_json_output(query: str, hits: List[Any], mode: str, answer: str = "") -> str: ...
def format_plain(hits: List[Any]) -> str: ...
```

**Critical — `format_json_output` signature is exactly:**
```python
def format_json_output(query: str, hits: List[Any], mode: str, answer: str = "") -> str:
```
Do NOT change argument order or add parameters.

---

## M2-B  Update `query.py`

1. Add import (after M1 imports):
```python
from util.formatting import (
    infer_source_type as _infer_source_type,
    fence_for as _fence_for,
    truncate_chunk as _truncate_chunk,
    format_result,
    format_markdown,
    format_concept_markdown,
    format_json_output,
    format_plain,
)
```

2. **Delete** from `query.py`:
   - `_infer_source_type` body (L614–L633)
   - `_fence_for` body (L636–L637)
   - `_truncate_chunk` body (L640–L663)
   - `format_result` body (L666–L741)
   - `format_markdown` body (~L1450–L1460)
   - `format_concept_markdown` body (~L1462–L1476)
   - `format_json_output` body (~L1478–L1490)
   - `format_plain` body (~L1492–L1505)

---

## M2-C  Update `mcp_server.py`

1. Add import (after M1 imports):
```python
from util.formatting import (
    infer_source_type as _infer_source_type,
    fence_for as _fence_for,
    truncate_chunk as _truncate_chunk,
    format_result,
)
```

2. **Delete** from `mcp_server.py`:
   - `_infer_source_type` body (L413–L432)
   - `_fence_for` body (L435–L438)
   - `_truncate_chunk` body (L439–L462)
   - `format_result` body (L465–L562)

3. `_structural_importance_int` stays in `mcp_server.py` — it is MCP-specific.
   The merged `format_result` in util reads `structural_importance` directly
   from metadata instead, so no import of that helper is needed.

---

## Acceptance Criteria

- [x] `util/formatting.py` exists, exports: `infer_source_type`, `fence_for`, `truncate_chunk`, `format_result`, `format_markdown`, `format_concept_markdown`, `format_json_output`, `format_plain`
- [x] `format_result` handles source types: `callee`, `code`, `domain_doc`, `theory`, `wiki`, `rfc`, `rally`, `customer`, `mib`, `community`, fallback
- [x] `format_json_output(query, hits, mode, answer="")` — correct argument order
- [x] `query.py`: no local `_infer_source_type`, `_fence_for`, `_truncate_chunk`, `format_result`, `format_markdown`, `format_concept_markdown`, `format_json_output`, `format_plain` bodies
- [x] `mcp_server.py`: no local `_infer_source_type`, `_fence_for`, `_truncate_chunk`, `format_result` bodies
- [x] `python3 -c "from util.formatting import format_result, format_json_output; print('OK')"` passes
- [x] `python3 -c "import ast; [ast.parse(open(f).read()) for f in ['query.py','mcp_server.py','util/formatting.py']]; print('ALL OK')"` passes
- [x] `util/formatting.py` does NOT import from `query.py` or `mcp_server.py`
