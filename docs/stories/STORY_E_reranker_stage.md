# STORY E: Cross-Encoder Reranker Stage After Retrieval

**Repository:** `mandnArgiTech/VVADomianRAG` branch `ngspice_rag`
**Priority:** High
**Estimated effort:** 4–5 hours
**Files to modify:** `mcp_server.py`, `query.py`, `requirements.txt`
**Files to create:** `reranker.py`, `tests/test_reranker.py`

---

## Business Context

The RAG pipeline currently scores results using either cosine similarity (dense-only) or Reciprocal Rank Fusion (dense + BM25). Both methods compare the query embedding against chunk embeddings **independently** — the embedding model never sees the query and chunk text together. This causes a specific failure mode in the ngspice→NodalAI workflow:

**Example:** Query "junction voltage clamping convergence failure". Dense search embeds this query and finds chunks about "junction capacitance" (high token overlap) ranking above the actual `DEVpnjlim` limiter function (which uses different vocabulary like "logarithmic compression", "critical voltage", "exponential interpolation"). A cross-encoder reranker reads the query AND each candidate chunk together as a pair, understanding that "clamping" relates to "limiting" and "convergence failure" relates to "prevent divergence" — semantic relationships that independent embeddings miss.

**Model choice:** `BAAI/bge-reranker-v2-m3` — 568M parameters, ~1.1GB VRAM at FP16. Runs on the RTX 4060 (inference GPU) without touching the A6000 (reserved for Gemma 3 chat). Scores 20 candidate chunks in <500ms on GPU.

---

## Scope

1. New module `reranker.py` wrapping `sentence-transformers` `CrossEncoder`
2. Post-retrieval reranking in both `mcp_server.py` and `query.py`
3. Opt-in via `RAG_RERANKER=1` env var (default OFF until validated)
4. Configurable model name, device, and top-K rerank count

## Scope — What This Is NOT

- Not replacing dense search or BM25 — reranking happens AFTER initial retrieval
- Not modifying the embedding model or ingest pipeline
- Not adding a new dependency unless `RAG_RERANKER=1` is set (lazy import)

---

## Acceptance Criteria

### AC-1: Reranker module with lazy loading

**Given** a new file `reranker.py`,
**When** imported,
**Then** it provides:

```python
class Reranker:
    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3",
                 device: str = "cuda:1",  # RTX 4060 — not cuda:0 which is A6000
                 use_fp16: bool = True):
        ...

    def rerank(self, query: str, documents: List[str],
               top_k: Optional[int] = None) -> List[Tuple[int, float]]:
        """Score query-document pairs. Return list of (original_index, score) sorted by score descending."""
        ...
```

The `CrossEncoder` model is loaded lazily on first `rerank()` call, not at import time. This means `import reranker` has zero startup cost when reranking is disabled.

### AC-2: Singleton reranker instance

**Given** multiple calls to the reranker within a session,
**When** `rerank()` is called,
**Then** the CrossEncoder model is loaded once and reused (module-level singleton pattern, same as how `hybrid_search.py` caches BM25 indexes).

### AC-3: Integration into `_sync_multi_search` (MCP server)

**Given** `RAG_RERANKER=1` env var is set,
**When** `_sync_multi_search` in `mcp_server.py` produces the initial ranked results (after RRF or dense-only scoring),
**Then**:
1. Take the top `RAG_RERANKER_CANDIDATES` results (default 30 — over-fetch to give the reranker a good pool)
2. Extract their `page_content` text
3. Call `reranker.rerank(query, texts, top_k=k)` where `k` is the requested result count
4. Reorder the results by reranker score
5. Return the reranked top-K

### AC-4: Integration into `_sync_multi_search` (query.py)

Same as AC-3 but in `query.py`'s `_sync_multi_search` function. Both files must stay in sync.

### AC-5: Env var configuration

| Variable | Default | Description |
|---|---|---|
| `RAG_RERANKER` | `0` | Set to `1` to enable reranking |
| `RAG_RERANKER_MODEL` | `BAAI/bge-reranker-v2-m3` | HuggingFace model name |
| `RAG_RERANKER_DEVICE` | `cuda:1` | PyTorch device (use `cuda:1` for RTX 4060, `cpu` if no second GPU) |
| `RAG_RERANKER_CANDIDATES` | `30` | How many candidates to over-fetch for reranking |
| `RAG_RERANKER_FP16` | `1` | Use FP16 for faster inference |

### AC-6: Graceful degradation

**Given** `RAG_RERANKER=1` but `sentence-transformers` is not installed,
**When** the reranker is first called,
**Then** it logs a warning `"Reranker enabled but sentence-transformers not installed. pip install sentence-transformers. Falling back to RRF/dense scoring."` and returns results in their original order.

### AC-7: Reranker does NOT touch exact chunk_name results

**Given** the "God mode" exact `chunk_name` pre-fetch results,
**When** reranking runs,
**Then** exact matches are excluded from reranking and prepended to the final results unchanged. Only the semantically-retrieved results go through the reranker.

### AC-8: Dependencies

**Given** `requirements.txt`,
**When** this story is complete,
**Then** `sentence-transformers>=3.0.0` is added with a comment `# optional: for RAG_RERANKER=1`

### AC-9: All existing tests pass

`pytest tests/` — 0 failures, ≥ 95% coverage on `ingest.py`.

---

## Implementation Guide

### Step 1: Create `reranker.py`

```python
"""
Cross-encoder reranker for post-retrieval re-scoring.

Lazy-loaded singleton: the model is not loaded until the first rerank() call.
Disabled by default — set RAG_RERANKER=1 to enable.
"""
from __future__ import annotations

import logging
import os
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("reranker")

_instance: Optional["Reranker"] = None


def get_reranker() -> Optional["Reranker"]:
    """Return the module-level Reranker singleton, or None if disabled."""
    global _instance
    enabled = os.environ.get("RAG_RERANKER", "0").strip().lower()
    if enabled not in ("1", "true", "yes"):
        return None
    if _instance is None:
        _instance = Reranker(
            model_name=os.environ.get("RAG_RERANKER_MODEL", "BAAI/bge-reranker-v2-m3"),
            device=os.environ.get("RAG_RERANKER_DEVICE", "cuda:1"),
            use_fp16=os.environ.get("RAG_RERANKER_FP16", "1").strip() in ("1", "true", "yes"),
        )
    return _instance


class Reranker:
    def __init__(self, model_name: str, device: str = "cuda:1", use_fp16: bool = True):
        self.model_name = model_name
        self.device = device
        self.use_fp16 = use_fp16
        self._model = None  # lazy

    def _ensure_loaded(self):
        if self._model is not None:
            return
        try:
            from sentence_transformers import CrossEncoder
            import torch

            dev = self.device if torch.cuda.is_available() else "cpu"
            self._model = CrossEncoder(
                self.model_name,
                device=dev,
                trust_remote_code=True,
            )
            if self.use_fp16 and dev != "cpu":
                self._model.model.half()
            logger.info("Reranker loaded: %s on %s (fp16=%s)", self.model_name, dev, self.use_fp16)
        except ImportError:
            logger.warning(
                "Reranker enabled but sentence-transformers not installed. "
                "pip install sentence-transformers. Falling back to original scoring."
            )
            self._model = None
        except Exception as exc:
            logger.warning("Failed to load reranker %s: %s", self.model_name, exc)
            self._model = None

    def rerank(
        self, query: str, documents: List[str], top_k: Optional[int] = None
    ) -> List[Tuple[int, float]]:
        """Score (query, doc) pairs. Returns [(original_index, score)] sorted by score descending."""
        self._ensure_loaded()
        if self._model is None or not documents:
            # Passthrough: return original order with dummy scores
            return [(i, 0.0) for i in range(min(top_k or len(documents), len(documents)))]

        pairs = [(query, doc) for doc in documents]
        scores = self._model.predict(pairs, show_progress_bar=False)

        indexed = [(i, float(s)) for i, s in enumerate(scores)]
        indexed.sort(key=lambda x: -x[1])

        if top_k is not None:
            indexed = indexed[:top_k]
        return indexed
```

### Step 2: Integration point in mcp_server.py

**CRITICAL:** `_sync_multi_search` has **two separate code paths** with **two separate return statements**:
- **Dense-only path** (when `use_hybrid` is False): assembles `regular` list and returns at ~line 704
- **Hybrid/RRF path** (when `use_hybrid` is True): assembles `regular` from `fused` list and returns at ~line 777

**The reranker must be applied in BOTH paths**, immediately before each `return exact + regular` statement. Use the exact same reranker block in both places:

```python
from reranker import get_reranker

# --- Reranker stage (AC-3) — insert BEFORE each "return exact + regular" ---
reranker = get_reranker()
if reranker is not None and regular:  # 'regular' = non-exact results
    cand_count = int(os.environ.get("RAG_RERANKER_CANDIDATES", "30"))
    to_rerank = regular[:cand_count]
    texts = [getattr(doc, "page_content", "") for doc, _, _ in to_rerank]
    ranked = reranker.rerank(query, texts, top_k=k)
    regular = [(to_rerank[idx][0], to_rerank[idx][1], to_rerank[idx][2]) for idx, score in ranked]

return exact + regular
```

Insert this block at **both** return points:
1. After `regular = [...]` at ~line 699–703, before the `return` at line 704
2. After `regular = [...]` at ~line 772–776, before the `return` at line 777

### Step 3: Same integration in query.py

`query.py`'s `_sync_multi_search` (line 828) has the **same dual-path structure** (dense-only and hybrid). Apply the identical reranker block before both return statements in `query.py` as well.

### Step 4: CrossEncoder API notes

The `sentence_transformers.CrossEncoder` is used (not `FlagEmbedding.FlagReranker`) to avoid adding another dependency. Key API behavior:
- `CrossEncoder.predict(pairs)` returns **raw logits** (unbounded floats) — higher means more relevant
- No sigmoid normalization is needed since we only care about relative ordering for re-ranking
- `trust_remote_code=True` is required for `bge-reranker-v2-m3`
- The model automatically handles tokenization and truncation to `max_length=512` tokens per pair

### Step 5: Update requirements.txt

Add:
```
sentence-transformers>=3.0.0  # optional: for RAG_RERANKER=1 cross-encoder reranking
```

---

## Test Plan

### File: `tests/test_reranker.py`

```
Test ID | Description | Approach
--------|-------------|----------
RR-01   | get_reranker returns None when RAG_RERANKER=0 | monkeypatch env to "0". Assert get_reranker() is None
RR-02   | get_reranker returns Reranker when RAG_RERANKER=1 | monkeypatch env to "1", mock CrossEncoder. Assert returns Reranker instance
RR-03   | Reranker.rerank returns correct ordering | Create Reranker with mock model. Set mock scores [0.1, 0.9, 0.5]. Assert order is [1, 2, 0]
RR-04   | Reranker.rerank respects top_k | 5 documents, top_k=2. Assert len(result) == 2
RR-05   | Reranker.rerank passthrough when model unavailable | Reranker with _model=None. Assert returns original order [(0,0.0), (1,0.0), ...]
RR-06   | Lazy loading: model not loaded at __init__ | Create Reranker. Assert _model is None
RR-07   | Lazy loading: model loaded on first rerank() | Create Reranker, mock CrossEncoder. Call rerank(). Assert _model is not None
RR-08   | Singleton: get_reranker returns same instance | Call get_reranker() twice. Assert same object
RR-09   | Graceful degradation when sentence-transformers missing | Mock ImportError on CrossEncoder import. Assert rerank returns passthrough order + logs warning
RR-10   | MCP _sync_multi_search applies reranker when enabled | Mock get_reranker to return a mock that reverses order. Assert final results are reversed vs without reranker
RR-11   | MCP preserves exact chunk_name results before reranked results | Mock search with 2 exact + 5 regular. Enable reranker. Assert exact results are first 2, unchanged
RR-12   | Env var RAG_RERANKER_CANDIDATES controls pool size | Set to "10". Assert only 10 candidates passed to reranker.rerank
RR-13   | Env var RAG_RERANKER_DEVICE defaults to cuda:1 | Don't set env var. Assert Reranker created with device="cuda:1"
```

### Manual validation

```bash
# Install dependency
pip install sentence-transformers

# Enable reranker
export RAG_RERANKER=1
export RAG_RERANKER_DEVICE=cuda:1  # RTX 4060

# Query with reranker
./query.sh semantic "diode junction voltage limiting divergence" --domain spice --chat

# Compare: disable reranker and run same query
export RAG_RERANKER=0
./query.sh semantic "diode junction voltage limiting divergence" --domain spice --chat
```

Expected: with reranker, `DEVpnjlim` and Chapter_05 chunks rank higher than generic "junction capacitance" chunks.

---

## VRAM Budget

| Component | GPU | VRAM |
|---|---|---|
| Gemma 3 27B QAT (chat) | cuda:0 (A6000 48GB) | ~29GB @ 64K ctx |
| mxbai-embed-large (embeddings) | cuda:0 (A6000 48GB) | ~1GB |
| bge-reranker-v2-m3 FP16 (reranker) | cuda:1 (RTX 4060 8GB) | ~1.1GB |
| **Total cuda:1** | | **~1.1GB / 8GB** |

The reranker fits comfortably on the RTX 4060 with 7GB headroom.

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Reranker adds latency per query | ~500ms for 30 candidates on GPU. Acceptable for interactive debugging. Disabled by default. |
| `sentence-transformers` is a heavy dependency (~500MB) | Listed as optional in requirements.txt. Only imported when `RAG_RERANKER=1`. |
| Reranker score disagrees with RRF score | Reranker score is authoritative — it reads both query and passage. RRF is a pre-filter to narrow candidates. |
| Model download on first use (~1.1GB) | HuggingFace cache. One-time download. |

---

## Definition of Done

- [ ] `reranker.py` exists with `Reranker` class and `get_reranker()` singleton
- [ ] Lazy loading: CrossEncoder not loaded until first `rerank()` call
- [ ] `_sync_multi_search` in `mcp_server.py` applies reranker when `RAG_RERANKER=1`
- [ ] `_sync_multi_search` in `query.py` applies reranker when `RAG_RERANKER=1`
- [ ] Exact chunk_name results excluded from reranking
- [ ] Graceful fallback when `sentence-transformers` not installed
- [ ] `sentence-transformers>=3.0.0` in `requirements.txt` (optional comment)
- [ ] All 13 new tests pass, all existing tests pass
