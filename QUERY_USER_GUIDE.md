# User guide: `query.sh` and `query.py`

Standalone **query** tools for **Universal Domain RAG**: semantic search, concept search, and database status **without** running the MCP server. They use the same Chroma collections and Ollama embedding model as ingestion ([`run.sh`](RUN_SH_USER_GUIDE.md)).
RAG_GUI_PORT=8501 ./gui.sh
---

## Prerequisites

1. **Portable bundle** — Run `./build.sh` so `Studio-Portable-RAG/Ollama/ollama` exists (or `Portable_RAG` fallback), same as [`run.sh`](RUN_SH_USER_GUIDE.md).
2. **Indexed data** — Run `./run.sh` (or equivalent) so `VectorDB` under the bundle contains Chroma collections.
3. **Embedding model** — The model used at ingest time must be available in Ollama (e.g. `ollama pull nomic-embed-text`). `query.py` auto-detects the model from `ingestion_config.json` or embedding dimension when possible.
4. **Tools** — `curl` for Ollama checks (`query.sh`). Readline support for interactive mode (standard on Linux).

---

## Quick start

```bash
./build.sh    # once
./run.sh --mode code   # or your ingest mode — once you have a VectorDB

# Single semantic query
./query.sh -q "how does STP work" -k 5

# Interactive REPL
./query.sh -i

# Database status (no embedding call for listing; still needs readable Chroma path)
./query.sh --mode status

# Concept search (metadata tag)
./query.sh --mode concept -q stp --domain nms
```

Run `query.sh` from the **DomainRAG repo root** (next to `Studio-Portable-RAG`), same as `run.sh`.

---

## `query.sh` vs `query.py`

| Use | When |
|-----|------|
| **`./query.sh ...`** | Normal use: sets `OLLAMA_MODELS`, `DB_PATH`, starts or reuses Ollama, copies `query.py` into the bundle, runs bundled Python. |
| **`python3 query.py ...`** | Advanced: you already have Ollama on `:11434` and env vars set; pass `--db-path` explicitly. |

Shell-only options are **removed** from the argument list before the rest is forwarded to `query.py`.

---

## `query.sh` options

| Option | Purpose |
|--------|---------|
| `--db-path PATH` | Vector database directory; exported as `DB_PATH`. Created if missing. Default: `<BaseDir>/VectorDB`. |
| `--model NAME` | Sets `EMBEDDING_MODEL` (must match ingest model). |
| `--no-ollama` | Do not start bundled Ollama; expect a server on `http://127.0.0.1:11434`. |
| `--ollama-timeout N` | Seconds to wait for Ollama when starting (default: 30). |
| `-h`, `--help` | Show `query.sh` usage (does not run `query.py`). |

All other arguments are passed through to `query.py`. To pass `--help` to `query.py`, use a delimiter so it is not consumed by the shell wrapper:

```bash
./query.sh -- --help
```

---

## `query.py` CLI reference

| Option | Description |
|--------|-------------|
| `-q`, `--query TEXT` | Search string (required unless `-i` or `--mode status`). In **concept** mode, this is the **concept id**. |
| `-m`, `--mode` | `semantic` (default), `concept`, `codebase`, or `status`. |
| `-t`, `--search-type` | For semantic/codebase: `auto`, `code`, `domain`, `troubleshoot`, `reference` (default: `auto`). |
| `-d`, `--domain` | Only collections whose name contains this substring (case-insensitive). |
| `-r`, `--repo` | Metadata filter: `repository` equals this value (semantic/codebase). |
| `-k`, `--top-k N` | Max hits (1–25, default 5). |
| `-f`, `--format` | `markdown` (default), `json`, or `plain`. |
| `-o`, `--output FILE` | Write results to a file instead of stdout. |
| `--no-color` | Reserved for future ANSI control (currently no-op). |
| `--db-path PATH` | Chroma persist directory (default: env `DB_PATH` or `./VectorDB` relative to cwd). |
| `--model NAME` | Override embedding model (default: auto-detect). |
| `--timeout SECS` | Per-query wall-clock timeout using `SIGALRM` (default: 120). **Unix only**; on Windows, timeout is not enforced. |
| `-i`, `--interactive` | Start interactive REPL (see below). |
| `-v`, `--verbose` | Debug logging on stderr. |
| `--quiet` | Fewer stderr banners; still prints results on stdout unless `-o` is used. |

---

## Search modes

| Mode | What it does | When to use |
|------|----------------|-------------|
| **semantic** | Embedding similarity across routed collections (`--search-type` controls which collections). | General questions across code + docs. |
| **codebase** | Same as semantic with `search_type=code` (code collections only). | Code-focused lookup. |
| **concept** | Chroma metadata `$contains` on the `concepts` field (pipe-delimited ids). | Find chunks tagged with a known concept id. |
| **status** | Prints collection chunk counts, source counts, last ingest dates, top concepts. | Health check; no query text required. Does **not** require Ollama (Chroma-only). |

---

## Output formats

- **markdown** — Rich blocks aligned with MCP `format_result` (headers, code fences where applicable).
- **json** — Machine-readable: `{"query": "...", "mode": "...", "results": [{ "content", "score", "source_type", "metadata", "collection" }]}`.
- **plain** — Compact text blocks separated by `---`, no markdown fences.

---

## Interactive REPL (`-i` / `--interactive`)

Launch:

```bash
./query.sh -i
# or
./query.sh --interactive --domain nms
```

- **Prompt:** `rag>`
- **Plain input:** treated as a **query** in the current mode (`semantic`, `concept`, or `codebase`).
- **History:** previous lines are saved with readline; session history file: **`~/.rag_query_history`** (up to 500 entries).
- **Ctrl+C:** cancels the current line or running query; does not exit the REPL.
- **Ctrl+D** or **`exit`** / **`quit`:** exit the REPL (history is saved).

### Slash commands

| Command | Description |
|---------|-------------|
| `/help` | List commands. |
| `/show` | Print current settings (`domain`, `repo`, `k`, `search_type`, `format`, `mode`, `timeout`). |
| `/status` | Print the same status table as `--mode status`. |
| `/set domain <name>` | Domain substring filter for collection names. |
| `/set k <N>` | Top-k (clamped to 25). |
| `/set type <auto\|code\|domain\|troubleshoot\|reference>` | Semantic routing. |
| `/set repo <name>` | Repository metadata filter. |
| `/set format <markdown\|json\|plain>` | Output format for results. |
| `/set mode <semantic\|concept\|codebase>` | Interactive search mode (not `status`; use `/status`). |
| `/set timeout <secs>` | Per-query timeout. |
| `/quit` or `/exit` | Leave the REPL. |

Example session:

```text
rag> /show
domain='' repo='' k=5 search_type='auto' format='markdown' mode='semantic' timeout=120
rag> Spanning tree root guard
[... markdown results ...]
rag> /set mode concept
OK: mode = 'concept'
rag> stp
[... concept hits ...]
rag> /quit
```

---

## Piping and scripting

```bash
# JSON for jq
./query.sh --quiet -q "API timeout" -f json | jq '.results[0].metadata.relative_path'

# Save report
./query.sh -q "memory leak" -o /tmp/rag-out.md

# Exit codes for automation
./query.sh -q "unlikely_xyz_not_found" ; echo $?
# 1 = no results (semantic/concept), 0 = status ok, etc.
```

---

## Exit codes (`query.py`)

| Code | Meaning |
|------|---------|
| 0 | Success (results found, or status printed). |
| 1 | No matching chunks (semantic/concept only). |
| 2 | Invalid arguments (e.g. missing `--query`). |
| 3 | Infrastructure error (bad DB path, Ollama down, Chroma failure, no collections). |
| 130 | Interrupted (`KeyboardInterrupt` / Ctrl+C in non-REPL run). |

`query.sh` forwards `query.py`’s exit code.

---

## Examples

```bash
# Semantic, default DB and model detection
./query.sh -q "BGP best path selection"

# Code collections only, more hits
./query.sh --mode codebase -q "mutex" -k 15

# Domain-scoped semantic search
./query.sh -q "alarm thresholds" -d nms -t domain

# Concept tag (pipe-aware storage in index)
./query.sh --mode concept -q forwarding_table

# JSON to stdout
./query.sh -q "config validation" -f json

# Status only
./query.sh --mode status

# Custom VectorDB and model
./query.sh --db-path /data/myvectordb --model mxbai-embed-large -q "test"

# External Ollama only
./query.sh --no-ollama -q "hello"

# Longer Ollama wait on slow machines
./query.sh --ollama-timeout 60 -q "snmp"
```

---

## Troubleshooting

| Symptom | What to check |
|---------|----------------|
| Portable RAG not found | Run `./build.sh`; confirm `Studio-Portable-RAG/Ollama/ollama` exists and is executable. |
| Ollama did not become ready | Port 11434 in use or firewall; try `curl -s http://127.0.0.1:11434/`. Use `--no-ollama` if you manage Ollama yourself. |
| Ollama not reachable (`query.py`) | Start Ollama before `query.py`, or use `query.sh` without `--no-ollama`. |
| Warmup skipped / embed errors | `ollama pull <model>` for the same model used during ingest. |
| DB path is not a directory | Fix `--db-path` or run from bundle with default `VectorDB`. |
| No Chroma collections | Run ingestion first (`./run.sh ...`). |
| Query times out | Increase `--timeout` or reduce load on Ollama/GPU. |
| Empty concept results | Verify concept id spelling; check `--domain` filter matches collection names. |

---

## Related files

| File | Role |
|------|------|
| [`run.sh`](RUN_SH_USER_GUIDE.md) | Ingestion into VectorDB. |
| [`mcp_server.py`](mcp_server.py) | Cursor MCP tools (`search_knowledge`, `search_concepts`); same search behavior as this CLI. |
| [`ingest.py`](ingest.py) | Ingestion pipeline; `--mode status` overlaps with `query.py --mode status`. |
