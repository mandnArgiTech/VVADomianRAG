# Studio-Portable-RAG

## Hybrid search (`search_knowledge`)

Dense Chroma retrieval is optionally combined with BM25 and Reciprocal Rank Fusion (RRF). Install the BM25 dependency in the same Python environment as the MCP server:

```bash
pip install rank-bm25
```

If `rank-bm25` is missing, set `HYBRID_SEARCH=0` for dense-only behavior, or install the package as above.

Optional tuning: `HYBRID_SEARCH`, `RRF_K` (default `60`), `HYBRID_DENSE_CANDIDATES`, `HYBRID_BM25_CANDIDATES`, `BM25_CACHE_DIR`.

### Tests

```bash
./Python/bin/python test_hybrid_search.py
```

Covers RRF, BM25 + repo filter, hybrid `_sync_multi_search` (with a constant embedding so BM25 breaks ties), and `HYBRID_SEARCH=0` dense-only via a subprocess.
