# Task: Build a Pocket Terminal RAG Chatbot for VVADomainRAG (NodalAI / ngspice / ArduPilot knowledge)

Build a local terminal chatbot that answers questions about the ngspice, NodalAI, ArduPilot (kinematica), MuJoCo, Nav2, and DART codebases using the existing VVADomainRAG ChromaDB indexes. The model is **Gemma 3 4B (SLM) served via Ollama**, loaded at `num_ctx=16384` with RAG-tuned sampling. The UI is **Textual** (terminal). Every design choice accounts for SLM limitations — this is not a GPT-4-class bot. The bot must be fast, reliable, and crash-free on modest hardware.

**Where this fits:** VVADomainRAG already has a FastMCP server that serves context to Cursor IDE via MCP protocol for NodalAI development on the A6000 (Gemma 3 27B QAT + mxbai-embed-large). This pocket bot is a **lightweight terminal companion** that runs anywhere — laptop, remote ssh session, or a second workstation — using the same ChromaDB index but with **Gemma 3 4B** so it fits in < 10GB RAM. Same retrieval, smaller brain.

## Non-Goals
- **Do not build ingestion.** Ingestion is handled by the main `ingest.py` / `run.sh` pipeline; the Chroma collections are already populated. Read-only consumer.
- **Do not change the index schema.** VVADomainRAG metadata fields already exist (Stories A–H); use them.
- **Do not add features I didn't ask for** (no multi-tenant, no admin panel, no feedback loops, no web UI, no MCP server — we already have that). Pocket scope only.
- **Do not compete with the MCP server in Cursor.** MCP serves Cursor with Gemma 3 27B. This pocket bot is the quick-look tool for when you're not in the IDE.

---

## Target Environment

- **Model**: `gemma3:4b` (Q4_K_M) via Ollama — NOT the 27B QAT used by Cursor
- **Model context window**: 131072 theoretical, **loaded at 16384 for this bot** (balances KV-cache RAM footprint and real usable context)
- **Embedding model**: `mxbai-embed-large` (1024-dim) — this is what VVADomainRAG uses (locked in by Story D/E). DO NOT use `nomic-embed-text`; retrieval will be broken because existing vectors are 1024-dim. Verify with `scripts/check_env.py` before first run.
- **Vector DB**: ChromaDB at `Studio-Portable-RAG/VectorDB` (same path used by `ingest.py` and `mcp_server.py`)
- **RAM footprint target**: < 10GB resident (Gemma 3 4B Q4_K_M ~3GB + 16K KV cache ~4–5GB + app < 500MB)
- **UI**: Textual (terminal, Python)
- **Concurrency**: single user, single concurrent LLM call

---

## Architecture (build and test each in order — do not skip ahead)

### 1. Configuration (`config.py`)

Single config file, `pydantic-settings`-backed, env-var overridable. Reads `VVADOMAINRAG_ROOT` env var defaulting to the repo root detected from CWD:

```python
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # --- Repository paths ---
    VVADOMAINRAG_ROOT: Path = Path.cwd()  # resolves to VVADomianRAG repo root
    CHROMA_PATH: Path = None              # derived: VVADOMAINRAG_ROOT / "Studio-Portable-RAG/VectorDB"

    # --- Ollama ---
    OLLAMA_HOST: str = "http://localhost:11434"
    LLM_MODEL: str = "gemma3:4b"
    LLM_NUM_CTX: int = 16384             # loaded context; KV cache sized to this
    LLM_MAX_TOKENS_OUT: int = 768        # keep outputs focused
    LLM_TIMEOUT_SEC: int = 45

    # Gemma 3 sampling (RAG-tuned defaults, NOT the model card defaults)
    # Model card defaults (temp=1.0, top_k=64, top_p=0.95) are for general chat
    # and cause hallucination in RAG. These RAG defaults prioritize grounding.
    LLM_TEMPERATURE: float = 0.2
    LLM_TOP_K: int = 40
    LLM_TOP_P: float = 0.9
    LLM_REPEAT_PENALTY: float = 1.1

    # --- Embeddings (LOCKED to match VVADomainRAG ingestion; see Stories D/E) ---
    EMBED_MODEL: str = "mxbai-embed-large"   # DO NOT change without re-ingestion
    EMBED_DIM: int = 1024
    EMBED_TIMEOUT_SEC: int = 5

    # --- Domain selection (spice | kinematica | mujoco | nav2 | dart | all) ---
    DEFAULT_DOMAIN: str = "spice"
    # Collections follow VVADomainRAG convention: {domain}_code, {domain}_domain
    # e.g. spice_code, spice_domain, kinematica_code, kinematica_domain

    # --- Retrieval ---
    TOP_K_RECALL: int = 30
    TOP_K_RERANK: int = 6                # sweet spot for Gemma 3 4B synthesis
    MIN_SIMILARITY: float = 0.25         # cosine distance floor
    CHUNK_TOKEN_BUDGET: int = 10000      # ~2K sys+query, ~3K history, ~1K answer buffer, ~10K chunks

    # Reuse VVADomainRAG's Story E reranker? Opt-in; off by default for pocket scope
    USE_CROSS_ENCODER_RERANK: bool = False
    RERANKER_MODEL: str = "BAAI/bge-reranker-v2-m3"
    RERANKER_DEVICE: str = "cpu"         # laptop default; cuda:0 on workstation

    # --- Caching ---
    CACHE_DB_PATH: Path = Path.home() / ".pocket_bot" / "cache.db"
    QUERY_CACHE_TTL_SEC: int = 3600
    SEMANTIC_CACHE_SIM_THRESHOLD: float = 0.95
    CACHE_MAX_ENTRIES: int = 2000
    EMBEDDING_CACHE_MAX_ENTRIES: int = 5000

    # --- Conversation ---
    MAX_HISTORY_TURNS_FULL: int = 6
    HISTORY_SUMMARY_TOKEN_BUDGET: int = 400
    HISTORY_TOTAL_TOKEN_BUDGET: int = 3000

    # --- UI ---
    UI_THEME: str = "dark"
    UI_REFRESH_HZ: int = 30

    class Config:
        env_prefix = "POCKET_"           # POCKET_LLM_MODEL overrides LLM_MODEL

    def __init__(self, **data):
        super().__init__(**data)
        if self.CHROMA_PATH is None:
            self.CHROMA_PATH = self.VVADOMAINRAG_ROOT / "Studio-Portable-RAG" / "VectorDB"
```

Validate at startup; fail fast with clear error if:
- Ollama unreachable
- `LLM_MODEL` not pulled (suggest `ollama pull gemma3:4b`)
- `EMBED_MODEL` not pulled (suggest `ollama pull mxbai-embed-large`)
- Chroma DB path doesn't exist
- No `{domain}_code` or `{domain}_domain` collections found
- Collection embedding dimension ≠ `EMBED_DIM` (1024)

### 2. Vector store abstraction (`vectorstore.py`)

Thin protocol so backend can be swapped later:

```python
from typing import Protocol
from dataclasses import dataclass

class VectorStore(Protocol):
    def query(self, embedding: list[float], top_k: int, filters: dict | None, collections: list[str]) -> list[Chunk]: ...
    def get(self, chunk_id: str, collection: str) -> Chunk | None: ...
    def count(self, collection: str) -> int: ...
    def list_collections(self) -> list[str]: ...
    def health(self) -> bool: ...

@dataclass
class Chunk:
    chunk_id: str
    text: str
    metadata: dict
    distance: float
    collection: str           # which collection it came from (spice_code / kinematica_domain / etc.)
```

Implement `ChromaStore` reading the existing VVADomainRAG Chroma collections. When a query requests domain `spice`, search across both `spice_code` and `spice_domain` (matches VVADomainRAG's `mcp_server.py` multi-collection search logic). When domain is `all`, search every `_code` and `_domain` collection.

Do NOT assume metadata schema. All metadata access must be None-safe (`metadata.get("structural_importance", 0.5)`). Use the VVADomainRAG fields from Stories A–H (see index schema section below).

### 3. Embedding service (`embeddings.py`)

Ollama embeddings client for `mxbai-embed-large`:
- Sync + async methods
- Retry: max 2, exponential backoff (0.5s, 2s)
- Per-call timeout
- Embedding cache integration (see cache layer)
- Truncate input to mxbai's 512-token limit (log warning)
- Normalize embeddings to unit length (cosine-ready)

### 4. Caching layer (`cache.py`)

SQLite-backed, WAL-mode, single-writer pattern. Cache DB lives at `~/.pocket_bot/cache.db` (user-scoped, separate from the shared VVADomainRAG ChromaDB):

```sql
CREATE TABLE embedding_cache (
  text_hash TEXT PRIMARY KEY,
  embedding BLOB NOT NULL,
  model TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  last_accessed INTEGER NOT NULL
);

CREATE TABLE query_cache (
  query_hash TEXT PRIMARY KEY,
  query_text TEXT NOT NULL,
  query_embedding BLOB NOT NULL,
  answer TEXT NOT NULL,
  retrieved_chunk_ids TEXT NOT NULL,    -- JSON: [{chunk_id, collection}]
  model TEXT NOT NULL,
  domain TEXT NOT NULL,                  -- "spice" | "kinematica" | ...
  filters_hash TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  last_accessed INTEGER NOT NULL,
  hit_count INTEGER DEFAULT 0
);

CREATE TABLE retrieval_cache (
  query_hash TEXT PRIMARY KEY,
  chunk_ids TEXT NOT NULL,               -- JSON: [{chunk_id, collection}]
  scores TEXT NOT NULL,
  domain TEXT NOT NULL,
  filters_hash TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  last_accessed INTEGER NOT NULL
);

CREATE INDEX idx_query_cache_created ON query_cache(created_at);
CREATE INDEX idx_query_cache_domain ON query_cache(domain);
CREATE INDEX idx_retrieval_cache_created ON retrieval_cache(created_at);
CREATE INDEX idx_embedding_cache_accessed ON embedding_cache(last_accessed);
```

Three lookup paths in order:
1. **Exact query cache** — normalize (lowercase, strip punct, collapse whitespace), sha256, lookup. Must also match `filters_hash` AND `domain` so spice queries don't collide with kinematica queries.
2. **Semantic query cache** — embed query, cosine against last 500 cached queries (held in an in-memory numpy array, refreshed on cache write), return if ≥ SEMANTIC_CACHE_SIM_THRESHOLD AND `filters_hash` + `domain` match.
3. **Retrieval cache** — same normalization + filters hash + domain; skips vector search if hit.

LRU eviction keyed on `last_accessed` when table exceeds cap. TTL enforced on read (delete-on-expired-hit, treat as miss).

Provide `stats()` returning `{embedding_hits, embedding_misses, query_hits, query_misses, retrieval_hits, retrieval_misses, total_size_mb, per_domain: {...}}`.

Provide `invalidate_all()`, `invalidate_domain(domain)`, `invalidate_older_than(ts)`.

Single DB connection with explicit lock for writes. No threaded writes without the lock.

### 5. Query router (`router.py`)

Pre-retrieval query analysis. **No LLM calls** — pure keyword + regex. Extracts filter hints and boost signals. Detects which domain the query is about AND pulls concept hints from the VVADomainRAG concept registries (Story G):

```python
@dataclass
class QueryIntent:
    raw_query: str
    normalized_query: str
    domain: str                   # "spice" | "kinematica" | "mujoco" | "nav2" | "dart"
    filters: dict                 # passed to vector store
    boost_fields: dict            # used by reranker
    detected_entities: list[str]  # ngspice function names, ArduPilot classes, etc.
    detected_concepts: list[str]  # from concept_registry.json for the domain
    intent_type: str              # "lookup" | "explain" | "list" | "general"
    filters_hash: str             # stable hash for cache keys
```

Detect per domain:

**spice (ngspice / NodalAI):**
- **Device keywords**: "diode"→D, "bjt"|"transistor"→Q, "mosfet"|"nfet"|"pfet"→M, "jfet"→J, "capacitor"→C, "resistor"→R, "inductor"→L
- **Algorithm keywords**: "newton"|"nr"|"raphson"→NR, "gmin"→gmin_stepping, "source step"→src_stepping, "limiter"|"clamp"→DEVpnjlim, "gear"→gear_method, "trapezoidal"→trap_method, "mna"→mna_solver
- **Function names**: CamelCase like `NIiter`, `CKTload`, `DIOload`, `DEVpnjlim`, `SMPluFac`
- **File patterns**: regex `[a-z]+load\.c` (dioload.c, bjtload.c)
- **Chapter refs**: `Chapter_\d+_*` for domain docs

**kinematica (ArduPilot):**
- **Vehicle keywords**: "rover", "plane", "copter", "sailboat", "balance bot"
- **Sensor keywords**: "imu", "gps", "barometer", "magnetometer", "rtk"
- **Algorithm keywords**: "ekf"|"navekf"→NavEKF3, "l1 nav"|"pure pursuit"→L1_Navigation, "mixer"→servo_mixer
- **Protocol keywords**: "mavlink", "dronecan", "crsf", "msp", "nmea", "uavcan"

**mujoco / nav2 / dart:**
- Smaller concept registries; use them as seed terms for boost matching

**Intent signals (all domains):**
- "show me the code" | "where is" | "which file" → bias `source_type=code`
- "how does" | "what is" | "why" | "explain" → no source_type bias, broader retrieval
- "list all" | "what are the" → bias higher TOP_K

**Domain auto-detect heuristic:**
- If query contains ngspice function names / device letters → spice
- If query contains ArduPilot class names / vehicle types → kinematica
- Else use DEFAULT_DOMAIN

User can override with explicit prefix: `/spice how does DIOload work?` or `/kinematica explain NavEKF3`.

### 6. Retriever + reranker (`retriever.py`)

**Stage 1 — Recall:**
- Check retrieval cache (by normalized query + filters_hash + domain) → hit? return cached chunk_ids
- Embed query (via embedding cache)
- Query vector store across both `{domain}_code` and `{domain}_domain` collections: `top_k=TOP_K_RECALL`, filters from intent
- Drop chunks with distance > (1 - MIN_SIMILARITY)

**Stage 2 — Metadata rerank** (reuse VVADomainRAG's Story A/B/H metadata):

```
score = 0.55 * normalized_similarity
      + 0.15 * structural_importance           (from Story A; default 0.5)
      + 0.10 * source_type_weight              (code=1.0, domain_doc=0.9, rfc=0.7, community=0.5)
      + 0.05 * chapter_match_bonus             (1.0 if Chapter_N mentioned in query matches metadata)
      + 0.05 * concept_match_bonus             (chunk has any detected_concept in metadata.concepts)
      + 0.05 * call_graph_bonus                (chunk is callee of a function mentioned in query, from Story B metadata.calls)
      + 0.05 * file_match_bonus                (path contains any detected_entity or dotted token)
```

Sort descending, keep TOP_K_RERANK. Return with score breakdowns for debug surfacing.

**Optional Stage 2b — Cross-encoder rerank (opt-in):**
If `USE_CROSS_ENCODER_RERANK=True`, re-order the top-10 of Stage 2 with `bge-reranker-v2-m3`. Skipped by default in pocket mode (CPU-only laptops) — the metadata rerank is usually enough for 4B model. Enable on a workstation with GPU.

**Stage 3 — Context packing:**

For each chunk, produce (format mirrors what VVADomainRAG's MCP server emits):

```
[CHUNK {i}] source={source_type} collection={collection} path={path}
{top_section}
{call_graph_hint}                    # "Callees (outgoing): fn1, fn2" from Story B
---
{chunk_text}
```

Where `top_section` is the topmost heading (for domain docs) or the function signature line (for code), derived from metadata `section` / `chunk_name`.

Greedily pack into CHUNK_TOKEN_BUDGET. Use `tiktoken` with a gpt-2 approximation tokenizer. If a single chunk exceeds 40% of budget, truncate it to that share and mark in debug.

Record chunk_id mapping `i → (chunk_id, collection)` for citation rendering.

### 7. LLM service (`llm.py`)

Ollama client wrapper:

- **Load model with explicit params**: on first call, send `options={"num_ctx": 16384, "temperature": 0.2, "top_k": 40, "top_p": 0.9, "repeat_penalty": 1.1}`. Gemma 3 in Ollama does NOT auto-load at 16K — must be set.
- Stream tokens via async generator
- `asyncio.Semaphore(1)` globally — second request waits or rejects (reject with clear error after 2s queue wait)
- Timeout: cancel stream on LLM_TIMEOUT_SEC
- Retry ONCE on connection error only (Ollama cold start); NOT on timeout/model error
- Measure and emit token counts

Expose:
```python
async def stream_chat(messages: list[dict], options: dict) -> AsyncIterator[StreamChunk]: ...

@dataclass
class StreamChunk:
    text: str
    done: bool
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    duration_ms: int | None = None
```

### 8. Prompts (`prompts.py`)

Short system prompts per domain. Load from `VVADomainRAG/system_prompts/{domain}_engineer.md` (these already exist from Story D — reuse them). Fallback to the built-in generic if the file is missing.

**Built-in generic system prompt:**

```
You are a focused assistant answering questions about the {domain} codebase. Answer strictly from the provided CONTEXT. If the answer is not in CONTEXT, say: "I don't have that in the indexed knowledge base." Cite sources inline as [1], [2] matching the CHUNK numbers shown. Be concise. Never invent file paths, class names, functions, structs, or symbols that are not in CONTEXT.
```

For `domain=spice`, the Story D prompt at `system_prompts/spice_engineer.md` is specific to ngspice/SPICE and already tuned — use it directly.

User prompt template:

```
CONTEXT:
{packed_chunks}

CONVERSATION SO FAR:
{history_or_empty}

QUESTION:
{user_query}

ANSWER (be concise, cite sources like [1], [2]):
```

No few-shot examples. Gemma 3 4B follows simple instructions adequately; few-shot bloats context without clear benefit at this scale.

### 9. Conversation manager (`conversation.py`)

Hybrid window + summarization (identical to original spec):

- Keep last `MAX_HISTORY_TURNS_FULL` (6) turns verbatim
- Older turns: maintain rolling summary, regenerated when a turn is evicted
- Summary uses same LLM, capped at `HISTORY_SUMMARY_TOKEN_BUDGET` (400 tokens)
- **Total history budget**: full turns + summary must fit under `HISTORY_TOTAL_TOKEN_BUDGET` (3000). If exceeded, trim oldest full turns first.
- Summary cached by hash of the turns-to-summarize
- Session-scoped, in-memory (no persistence)
- **Domain switch clears history** — switching from `/spice` to `/kinematica` starts a fresh conversation (mixed-domain context confuses 4B)

```python
class Conversation:
    def add_turn(self, user: str, assistant: str, domain: str) -> None: ...
    def get_context(self) -> str: ...
    def clear(self) -> None: ...
    def switch_domain(self, new_domain: str) -> None: ...   # clears if different
    def token_count(self) -> int: ...
```

### 10. Answer orchestrator (`answer.py`)

End-to-end pipeline:

```python
async def answer(query: str, conversation: Conversation) -> AsyncIterator[AnswerEvent]:
    yield StageEvent("routing")
    intent = router.route(query)        # resolves domain, filters, concepts

    yield DomainEvent(intent.domain)    # UI updates domain badge

    yield StageEvent("cache_lookup")
    cached = cache.lookup(intent)
    if cached:
        yield CachedAnswerEvent(cached)
        return

    yield StageEvent("retrieving")
    chunks = await retriever.retrieve(intent)

    yield RetrievedChunksEvent(chunks)

    yield StageEvent("generating")
    async for stream_chunk in llm.stream_chat(...):
        yield TokenEvent(stream_chunk.text)

    yield FinalEvent(full_answer, citations, debug)
    cache.store(intent, full_answer, chunks)
```

Events the UI handles:
- `StageEvent(name)` — status indicator
- `DomainEvent(domain)` — update domain badge (spice / kinematica / mujoco / nav2 / dart)
- `RetrievedChunksEvent(chunks)` — populate citation panel
- `TokenEvent(text)` — stream response
- `CachedAnswerEvent(answer)` — render immediately
- `FinalEvent(answer, citations, debug)` — finalize, record metrics
- `ErrorEvent(stage, message, recoverable)` — user-visible error

Every stage has its own timeout. Errors at any stage become `ErrorEvent` with a recoverable flag; the UI never sees an exception.

### 11. UI (`app.py`) — Textual

Textual app with a three-pane layout. Adds a **domain badge** next to the status dot (absent from original spec):

```
┌─────────────────────────────────────────────────────────────────────┐
│ VVADomainRAG Pocket │ 🟢 ready │ spice │ gemma3:4b │ ctx 16K │ 14/3 │
├──────────────────────────────────────┬──────────────────────────────┤
│                                      │  CITATIONS                   │
│  Chat                                │  ──────────────              │
│                                      │  [1] spice_code              │
│  > how does DIOload clamp vd?        │      path=dio/dioload.c      │
│                                      │      score=0.91              │
│  ▼ retrieving... [6 chunks, 312ms]   │      Callees: DEVpnjlim      │
│                                      │                              │
│  DIOload clamps the junction voltage │  [2] spice_domain            │
│  by calling DEVpnjlim() [1] before   │      path=Chapter_128_Diode… │
│  evaluating the exponential. The     │      score=0.87              │
│  limiter applies vd' = vdold + Vt·   │                              │
│  log(1 + (vd-vdold)/Vt) when vd>vcrit│  [3] spice_code              │
│  per the Shockley derivation in [2]. │      path=devsup.c           │
│                                      │      score=0.82              │
├──────────────────────────────────────┴──────────────────────────────┤
│ > ▊                                                                  │
└─────────────────────────────────────────────────────────────────────┘
```

**Widgets:**
- **Header bar**: title, status dot, **domain badge** (spice/kinematica/mujoco/nav2/dart/all), model name, ctx size, cache hits/misses
- **Chat pane** (`RichLog` or custom `ScrollableContainer` with `Markdown` widgets per message): renders markdown, streams incrementally, inline citation rendering as `[1]` `[2]`
- **Citations pane** (`VerticalScroll` with `Collapsible` per citation): number, collection, path, score breakdown, Call graph hints (from Story B `calls` metadata), expandable chunk text preview
- **Input bar** (`Input` widget): single-line; Enter to send, Shift+Enter = newline (implement via Ctrl+M toggle)
- **Footer / command bar**: keybind hints

**Key bindings:**
- `Enter` — send
- `Ctrl+L` — clear conversation
- `Ctrl+D` — toggle debug panel (stage timings, router intent, reranker scores, Chroma distances)
- `Ctrl+C` — graceful quit
- `Ctrl+R` — regenerate last answer (bypass cache)
- `Ctrl+K` — clear caches (with confirm prompt)
- `Tab` / `Shift+Tab` — move focus between panes
- `Ctrl+P` — open domain picker (select spice / kinematica / mujoco / nav2 / dart / all)

**Slash commands (typed into input bar):**
- `/spice <query>` — force spice domain for this query
- `/kinematica <query>` — force kinematica (ArduPilot) domain
- `/mujoco <query>` | `/nav2 <query>` | `/dart <query>`
- `/all <query>` — search all domains (expensive, rarely useful for SLM)
- `/stats` — show cache stats inline
- `/help` — show help text inline

**Streaming:**
- While LLM streams, append tokens to the latest chat message. Use Textual's `call_from_thread` or async workers — **do not block the event loop**.
- During retrieval, show a spinner with status ("retrieving spice_code + spice_domain...").
- Populate the citations pane as soon as retrieval completes, before the LLM emits its first token.

**Status dot states:**
- 🟢 ready
- 🟡 retrieving
- 🟠 generating
- 🔵 cache hit
- 🔴 error

**Startup checks visible in UI:**
- Ollama reachable
- `gemma3:4b` loaded (offer auto-pull with confirm)
- `mxbai-embed-large` reachable (offer auto-pull with confirm)
- Chroma collections present — list them with counts:
  ```
  ✓ spice_code (12845 chunks)
  ✓ spice_domain (2134 chunks)
  ✓ kinematica_domain (3287 chunks)
  — kinematica_code (not ingested)
  — mujoco_code / mujoco_domain (not ingested)
  ```
- Embedding dimension check: query any chunk, verify embedding dim == 1024

If any critical check fails: blocking error screen with retry/quit. Never start accepting queries in a broken state.

**Terminal compatibility:**
- Works in any ANSI terminal ≥ 80×24
- Handle terminal resize
- Degrade gracefully on terminals without Unicode (fall back to ASCII status indicators)
- Respect `NO_COLOR` env var

### 12. Error handling & crash avoidance

- **Every external call wrapped** in try/except with specific exception types. Never let anything propagate to Textual's event loop.
- **Global asyncio exception handler**: log + convert to `ErrorEvent`, never crash the app.
- **Signal handlers**: `SIGINT`/`SIGTERM` trigger graceful shutdown — cancel in-flight LLM stream, close DB connections, flush cache stats to log, exit cleanly.
- **Memory guard**: before each retrieval, check process RSS via `psutil`. If > 85% of total system RAM, trigger cache trim and log warning. If > 95%, refuse new queries.
- **Cold-start tolerance**: first query after startup is slow (Ollama model load + first embedding). Show clear "warming up..." status; don't time out on first call (use 2× normal timeout).
- **Structured logging**: stdlib logging + JSON formatter to `~/.pocket_bot/pocket_bot.log`, rotating 10MB × 3 files. Log stage timings, cache hits, retrieval scores (top 6), LLM latency, errors. **No raw queries logged by default** (privacy); enable via `LOG_QUERIES=1` env var.
- **No crash on malformed chunk metadata** — every metadata field access defaults safely. This is critical because VVADomainRAG metadata schema evolves (Stories A–H added fields over time) and older chunks may be missing newer fields.

### 13. Tests (`tests/`)

Fast unit tests (target < 3s total):
- `test_router.py` — parameterized intent extraction per domain (ngspice function names, ArduPilot classes, Kafka/MuJoCo/Nav2 patterns)
- `test_reranker.py` — deterministic score math on synthetic chunks; verify Story B `calls` bonus, Story A `structural_importance` weighting
- `test_cache.py` — hit/miss/TTL/eviction, filter-hash collision, per-domain invalidation
- `test_packing.py` — token budget enforcement, single-chunk oversize truncation, call-graph hint injection
- `test_conversation.py` — window eviction, summary trigger, token budget, domain-switch clears
- `test_vectorstore.py` — collection filtering (spice_code + spice_domain only), metadata None-safety

Integration smoke test (`scripts/smoke_test.py`, gated by env flag `POCKET_BOT_INTEGRATION=1`):
- Hits real Ollama + real VVADomainRAG Chroma
- Runs 5 canned queries **per domain available**:
  - spice: "How does DIOload clamp junction voltage?"
  - spice: "What does NIcomCof do for Gear integration?"
  - kinematica: "How does ArduRover compute L1 navigation?" (if ingested)
- Asserts: non-empty answer, latency < 20s per query (4B is slower than 27B), citations present
- Prints per-query telemetry

### 14. Scripts (`scripts/`)

- `smoke_test.py` — end-to-end sanity check across available domains
- `cache_stats.py` — print cache hit rates, sizes, top hit queries, per-domain breakdown
- `warmup.py` — pre-embed common queries from `warmup_queries.txt` (one file per domain: `warmup_spice.txt`, `warmup_kinematica.txt`)
- `check_env.py` — verifies Ollama up, `gemma3:4b` pulled, `mxbai-embed-large` pulled, Chroma populated, lists available domain collections, **verifies embedding dim is 1024**, returns exit 0/1

---

## Index schema (from VVADomainRAG — None-safe everywhere)

Each Chroma document: `text` + `metadata`. Expected metadata fields (from Stories A–H):

**Common (all chunks):**
- `chunk_id` (str) — primary key
- `source_type` (str) — "code" | "domain_doc" | "rfc" | "community"
- `path` (str) — source file path
- `repository` (str) — e.g., "spicelib", "spice", "ardupilot"
- `chunk_name` (str) — function name / section heading

**Code chunks (spice_code, kinematica_code, etc.) — from Stories A, B, H:**
- `chunk_type` (str) — "function_definition" | "declaration" | "file_preamble" | "core_constant" | "class_definition"
- `structural_importance` (float 0..1) — from Story A, default 0.5
- `calls` (str, comma-separated) — from Story B: outgoing function calls
- `dependencies` (str, comma-separated) — from Story A: `#include` refs

**Domain doc chunks (spice_domain, kinematica_domain, etc.) — from Story C:**
- `chapter_number` (int) — e.g., 128
- `chapter_title` (str) — e.g., "Diode Core Mathematics and DC"
- `section` (str) — top-level section heading
- `device_family` (str) — e.g., "diode", "bjt", "rover"
- `source_c_files` (str, comma-separated) — which C files this chapter documents
- `concepts` (str, comma-separated) — from concept registry

Missing fields must not raise. All access via `.get(..., default)`.

---

## Project layout

```
pocket_bot/                          # Standalone Python package
├── pyproject.toml
├── README.md
├── KNOWN_ISSUES.md
├── config.py
├── app.py                           # Textual App entry
├── ui/
│   ├── __init__.py
│   ├── chat_view.py
│   ├── citations_view.py
│   ├── header.py
│   ├── input_bar.py
│   └── domain_picker.py             # Ctrl+P domain selector
├── vectorstore.py
├── embeddings.py
├── cache.py
├── router.py
├── retriever.py
├── llm.py
├── prompts.py
├── conversation.py
├── answer.py
├── logging_setup.py
├── tests/
│   ├── conftest.py
│   ├── test_router.py
│   ├── test_reranker.py
│   ├── test_cache.py
│   ├── test_packing.py
│   ├── test_conversation.py
│   └── test_vectorstore.py
└── scripts/
    ├── smoke_test.py
    ├── cache_stats.py
    ├── warmup.py
    ├── check_env.py
    ├── warmup_spice.txt
    └── warmup_kinematica.txt
```

**Placement in your repos:**
- Put `pocket_bot/` as a subdirectory under `VVADomianRAG/` (it consumes the VVADomianRAG Chroma DB directly)
- Do NOT mix with `Studio-Portable-RAG/Python/` (that's the ingestion venv). Use a separate venv.

## Dependencies (pin minor versions)

```
python >= 3.11
textual ~= 0.82              # terminal UI framework
ollama ~= 0.3                # Ollama Python client
chromadb ~= 0.5              # MUST match version used by VVADomainRAG
pydantic-settings ~= 2.4
numpy ~= 1.26
tiktoken ~= 0.7              # gpt-2 tokenizer for budget counting
aiohttp ~= 3.9
psutil ~= 6.0
pytest ~= 8.3
pytest-asyncio ~= 0.24
rich ~= 13.7
# Optional: cross-encoder reranker (Story E reuse)
sentence-transformers ~= 3.0  # only if USE_CROSS_ENCODER_RERANK=True
```

## README must cover

1. **Prerequisites**:
   - Ollama running
   - `gemma3:4b` pulled (`ollama pull gemma3:4b`)
   - `mxbai-embed-large` pulled (`ollama pull mxbai-embed-large`)
   - VVADomainRAG ingestion complete (at least one `{domain}_code` or `{domain}_domain` collection populated)
2. **Why mxbai-embed-large (locked)**: VVADomainRAG ingested with mxbai (1024-dim). Using nomic-embed-text (768-dim) = dimension mismatch = broken retrieval.
3. **Difference from the MCP server in Cursor**: Cursor uses Gemma 3 27B QAT on the A6000 via MCP. Pocket bot uses Gemma 3 4B for laptop / ssh use. Same ChromaDB, smaller model.
4. **First-run**: `python -m pocket_bot.scripts.check_env` before launching
5. **Launch**: `python -m pocket_bot.app`
6. **Config env vars** — full table with `POCKET_` prefix
7. **Key bindings** — full table including Ctrl+P domain picker and slash commands
8. **Cache management**: clear via `Ctrl+K`, stats via `cache_stats.py`, per-domain invalidation
9. **Troubleshooting**:
   - Ollama down
   - Wrong embedding model (garbage retrieval) — how to detect via check_env
   - Empty Chroma — run VVADomainRAG ingestion first
   - Dimension mismatch error — re-ingest with mxbai-embed-large
   - Textual rendering issues in certain terminals
10. **Known limits**: single-user, pocket scope, Gemma 3 4B synthesis quality ceiling, 16K ctx ceiling, no cross-domain synthesis
11. **Why these Gemma sampling defaults** (not the model card defaults): RAG grounding requires low temperature

---

## Rules

1. Every async call has a timeout. No bare `await` on external services.
2. Every SQLite write is WAL-mode and single-writer.
3. Never load the entire Chroma collection into memory. Query-by-query only.
4. **Always prefix chunks with `top_section` and `call_graph_hint`** — VVADomainRAG Stories A–H baked these in for grounding. Don't bypass them.
5. Never exceed `CHUNK_TOKEN_BUDGET`. Measure with tiktoken, don't guess.
6. Every user-visible error tells the user what happened and what to do. No raw tracebacks in the UI.
7. No telemetry, no analytics, no external network calls other than Ollama and local Chroma.
8. No `TODO` / `FIXME` in shipped code — resolve or file in `KNOWN_ISSUES.md`.
9. Stream everything streamable. UI must never feel frozen, even on cold cache.
10. Textual event loop must never block. All I/O in workers or `asyncio.to_thread`.
11. Build modules in the order listed (config → vectorstore → embeddings → cache → router → retriever → llm → prompts → conversation → answer → UI). Do NOT touch the UI until `answer()` works end-to-end in a script.
12. Log Gemma 3's load-time options on first startup to verify `num_ctx=16384` was actually applied.
13. **Read-only consumer**: pocket bot never writes to the VVADomainRAG ChromaDB. All writes go to the pocket bot's own SQLite cache.
14. **Reuse VVADomainRAG system prompts** (`system_prompts/{domain}_engineer.md`) when present.

## Acceptance criteria

- `scripts/check_env.py` exits 0 on a properly configured system; lists all domain collections with chunk counts
- `scripts/smoke_test.py` passes 5 canned queries per available domain with latency < 20s each
- `python -m pocket_bot.app` launches into Textual UI, shows ready status with domain badge, accepts a query, streams an answer with citations
- `/spice` and `/kinematica` slash commands switch domain correctly
- Ctrl+C exits cleanly (no tracebacks, DB connections closed)
- Process RSS stays under 10GB during typical use
- All unit tests pass in < 3s
- On Ollama down: clear error in UI, retry button, no crash
- On dimension mismatch (embedding model change): check_env reports the mismatch clearly; bot refuses to start
- On empty Chroma: check_env suggests running VVADomainRAG ingestion first

**Begin with** `config.py` + `vectorstore.py` + `scripts/check_env.py` + `scripts/smoke_test.py`. Get a chunk-out-of-VVADomainRAG-Chroma round trip working before anything else. Then build inward: embeddings, cache, router, retriever, LLM, answer pipeline. UI last. Report progress after each module.
