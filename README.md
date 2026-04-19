# DomainRAG

Universal **domain-aware RAG** for code, documentation, RFCs, MIBs, tickets, and wiki content. It ingests heterogeneous sources into **ChromaDB** collections, serves them through an **MCP server** for Cursor (and other MCP clients), and includes a **CLI query** tool for ad-hoc retrieval.

## Features

- **Multi-mode ingestion** (`ingest.py` / `run.sh`): code, domain docs, theory, RFCs, Rally, customer tickets, MIBs, Confluence wiki, release notes, community threads, and more.
- **Chunking**: AST-aware Python; language splitters for JS/TS/C/C++/Java; RFC-aware and markdown-domain chunking (including diagram masking for Mermaid/HTML blocks).
- **Vector store**: Chroma persistent collections with deterministic chunk IDs and checkpointing.
- **Embeddings**: Ollama (`langchain-ollama`) — e.g. `nomic-embed-text`, `mxbai-embed-large`.
- **MCP server** (`mcp_server.py`): `search_knowledge`, `search_codebase`, `search_concepts`, `feed_domain_doc`, stats, and hybrid dense+BM25 search when `rank-bm25` is installed (see `hybrid_search.py` and `Studio-Portable-RAG/README.md`).
- **Standalone query CLI** (`query.py` / `query.sh`): same search semantics without running the MCP server.

## Requirements

- **Python 3.10+**
- **Ollama** running locally (default embed API `http://127.0.0.1:11434`)
- Dependencies: see [`requirements.txt`](requirements.txt)

```bash
pip install -r requirements.txt
```

Development / tests:

```bash
pip install -r requirements-dev.txt
pytest tests/
```

If global pytest plugins (e.g. ROS `launch_testing`) break collection:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest tests/
```

Coverage is enforced at **≥95%** for `ingest.py` via `pyproject.toml` (some optional branches use `# pragma: no cover`).

## Quick start

### 1. Ingest content

Linux/macOS (uses portable layout under `Studio-Portable-RAG` when present — see `run.sh`):

```bash
./run.sh --mode domain --domain general --source ./path/to/markdown
```

See [`RUN_SH_USER_GUIDE.md`](RUN_SH_USER_GUIDE.md) for modes, flags, and Ollama notes.

### Multi-Domain Ingestion

All domains can share the same embedding model (set via `--model` on `./run.sh` or `EMBEDDING_MODEL`).

```bash
# All domains use the same embedding model (example)
export EMBEDDING_MODEL=mxbai-embed-large

# SPICE (ngspice + NodalAI)
./run.sh --mode code --domain spice --source /path/to/ngspice/src
./run.sh --mode code --domain spice --source /path/to/NodalAI/ecad
./run.sh --mode domain --domain spice --source ./Studio-Portable-RAG/DomainDocs/ngspice

# Kinematica (ArduPilot / ArduRover)
./run.sh --mode code --domain kinematica --source /path/to/ardupilot
./run.sh --mode domain --domain kinematica --source ./Studio-Portable-RAG/DomainDocs/kinematica

# MuJoCo
./run.sh --mode code --domain mujoco --source /path/to/mujoco/src

# Nav2 (ROS 2 Navigation)
./run.sh --mode code --domain nav2 --source /path/to/navigation2

# DART
./run.sh --mode code --domain dart --source /path/to/dart
```

Use `./query.sh` / MCP `search_knowledge` with the same `--domain` value so collection routing matches the ingest prefix (`{domain}_code`, `{domain}_domain`, etc.).

### Removing stale Chroma chunks

If you ingested paths you later want excluded (e.g. ngspice `src/frontend/`), you can delete matching rows before re-ingesting. Example:

```python
# Manual ChromaDB cleanup example
import chromadb

client = chromadb.PersistentClient(path="./Studio-Portable-RAG/VectorDB")
coll = client.get_collection("spice_code")
results = coll.get(where={"relative_path": {"$contains": "frontend/"}}, include=[])
if results["ids"]:
    coll.delete(ids=results["ids"])
```

Adjust `path`, collection name, and the `where` filter to match your metadata (`relative_path`, `source`, etc.).

### 2. Query from the shell

```bash
./query.sh --help
./query.sh semantic "your question" --domain general
```

See [`QUERY_USER_GUIDE.md`](QUERY_USER_GUIDE.md) for interactive REPL and output formats.

### 3. Enterprise Code Intelligence Dashboard (Web UI)

Local FastAPI server + single-page UI (`gui_backend.py`, `index.html`) for live ingestion logs and hybrid-search chat.

```bash
pip install -r requirements.txt   # includes fastapi, uvicorn
cd /path/to/DomainRAG
uvicorn gui_backend:app --host 127.0.0.1 --port 8501
```

Open **http://127.0.0.1:8501/** in a browser. Ensure **Ollama** is running on `:11434` before using search/chat.

Optional environment:

| Variable | Purpose |
|----------|---------|
| `RAG_GUI_DB_PATH` | Chroma persist directory (default: `Studio-Portable-RAG/VectorDB` under repo root) |
| `RAG_GUI_SOURCE_BASE` | Root folder for the ingestion file browser (default: `Studio-Portable-RAG/Codebase` or `./Codebase`) |
| `EMBEDDING_MODEL` | Embedding model name (same as CLI) |

The UI streams ingestion stdout over SSE and streams LLM tokens when chat mode is enabled. **Do not expose this server to the internet** — it has no authentication. Use `--host 127.0.0.1` (as above), not `0.0.0.0`, unless you fully understand the risk.

**Reliability notes:** The dashboard retries when the vector database is briefly locked, pauses search/chat while ingestion runs (with a clear on-screen message), checks database paths so a typo does not create stray folders (except the optional path you type in the form), sanitizes model output in the browser, and trims very long ingest logs so the page stays responsive.

**Chat models:** Default answer model is **`qwen2.5-coder:32b`** on local Ollama (`ollama pull qwen2.5-coder:32b`). Embeddings still use your configured embed model on Ollama. You can instead choose **Claude (Anthropic)** or **DeepSeek** in the sidebar and paste an API key (optional “remember in browser”). Install `anthropic` and `openai` via `requirements.txt` for those providers.

### 4. Cursor / MCP

Point Cursor’s MCP config at your Python and `mcp_server.py`, and set env vars such as `DB_PATH`, `OLLAMA_EXE`, `OLLAMA_MODELS`, `EMBEDDING_MODEL`. Example pattern:

```json
{
  "mcpServers": {
    "codebase-rag": {
      "command": "/path/to/python3",
      "args": ["/path/to/mcp_server.py"],
      "cwd": "/path/to/project-or-portable-root",
      "env": {
        "DB_PATH": "/path/to/VectorDB",
        "OLLAMA_EXE": "/path/to/ollama",
        "EMBEDDING_MODEL": "nomic-embed-text"
      }
    }
  }
}
```

Use natural language in chat; the agent calls tools like **`search_knowledge`** (with `search_type`: `auto`, `code`, `domain`, `reference`, `troubleshoot`, etc.) and **`search_concepts`**.

## Repository layout

| Path | Role |
|------|------|
| `ingest.py` | CLI ingestion, chunking, checkpoints, Chroma upsert |
| `mcp_server.py` | MCP tools + Ollama/Chroma lifecycle |
| `domain_feeder.py` | Single-file domain feed helper for MCP |
| `query.py` / `query.sh` | Standalone RAG query CLI |
| `hybrid_search.py` | Optional BM25 + RRF fusion |
| `run.sh` / `run.ps1` | Ingest runner (Ollama + Python) |
| `build.sh` / `build.ps1` | Portable environment bootstrap |
| `tests/` | Pytest suite for `ingest.py` |
| `Studio-Portable-RAG/` | Optional portable Python/Ollama/models/DB tree (large; mostly gitignored) |

## Environment variables (runtime)

Common examples (not exhaustive — see scripts and `mcp_server.py`):

| Variable | Purpose |
|----------|---------|
| `DB_PATH` | Chroma persistence directory |
| `EMBEDDING_MODEL` | Ollama embedding model name |
| `OLLAMA_EXE` / `OLLAMA_MODELS` | Ollama binary and models directory |
| `SOURCE_FOLDER` | Default ingest source (legacy) |
| `RALLY_API_KEY` / `CONFLUENCE_*` | Optional remote ingest modes |
| `HYBRID_SEARCH` | `1` to enable hybrid search when `rank-bm25` is installed |

## Git: commit identity and authenticated push

**Upstream repository:** [https://github.com/mandnArgiTech/VVADomianRAG](https://github.com/mandnArgiTech/VVADomianRAG)

Use **`GIT_USER`** and **`GIT_PAT`** (GitHub personal access token) for HTTPS push. Optionally set **`GIT_EMAIL`** for commit author email.

```bash
export GIT_USER="deviprasad2002"
export GIT_PAT="ghp_xxxxxxxxxxxxxxxxxxxx"   # fine-scoped PAT; never commit this
export GIT_EMAIL="you@example.com"        # optional; default shown below

git config user.name "$GIT_USER"
git config user.email "${GIT_EMAIL:-$GIT_USER@users.noreply.github.com}"
```

Create the GitHub repository (empty) if needed, then add the remote and push (`GIT_REPO_FULLNAME` is `owner/repo`). For this project:

```bash
export GIT_REPO_FULLNAME="mandnArgiTech/VVADomianRAG"
git remote add origin "https://${GIT_USER}:${GIT_PAT}@github.com/${GIT_REPO_FULLNAME}.git"
git branch -M main
git push -u origin main
```

Alternatively set a full URL once:

```bash
export GIT_REMOTE_URL="https://${GIT_USER}:${GIT_PAT}@github.com/owner/DomainRAG.git"
git remote add origin "$GIT_REMOTE_URL"
git push -u origin main
```

**Security:** Do not store `GIT_PAT` in the repo. Use a secret manager or CI secrets. Revoke the PAT if it is ever leaked.

Helper script (same variables; does **not** print your token):

```bash
export GIT_USER="deviprasad2002"
export GIT_PAT="ghp_xxxxxxxx"
export GIT_REPO_FULLNAME="mandnArgiTech/VVADomianRAG"
./scripts/push-to-github.sh
```

## Documentation

- [`RUN_SH_USER_GUIDE.md`](RUN_SH_USER_GUIDE.md) — ingestion runner
- [`QUERY_USER_GUIDE.md`](QUERY_USER_GUIDE.md) — query CLI and REPL
- [`implementation_review.md`](implementation_review.md) — design notes

## License

Add a `LICENSE` file if you intend to open-source this project.
