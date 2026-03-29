# User guide: `run.sh`

Linux ingestion runner for **Universal Domain RAG**. It configures the portable Studio layout, starts or reuses **Ollama**, copies project Python assets into the bundle, and runs `ingest.py`.

Windows users: see `run.ps1` for the same workflow with PowerShell syntax.

---

## Prerequisites

1. **Build the portable bundle first**  
   Run `./build.sh` from the repo root. The script looks for an executable Ollama binary at:

   - `Studio-Portable-RAG/Ollama/ollama`, or  
   - `Portable_RAG/Ollama/ollama` (fallback)

2. **Tools used by the script**  
   - `curl` — Ollama health checks and embed warmup  
   - `python3` — optional JSON pretty-print for `api/ps` output  
   - `nvidia-smi` — optional; GPU info only (script still runs on CPU if missing)  
   - `realpath` — optional; improves `--source` path resolution  

---

## Quick start

```bash
# From the DomainRAG repo root (same directory as run.sh)
./build.sh          # once
./run.sh --mode code
./run.sh --mode status
```

`run.sh` must be run from a context where `Studio-Portable-RAG` (or `Portable_RAG`) exists **next to** `run.sh`, or the script cannot find the base directory.

---

## What the script does (three phases)

| Phase | Action |
|-------|--------|
| **1** | Sets `OLLAMA_MODELS`, embedding model, worker counts, `DB_PATH`, and resolves `SOURCE_FOLDER` (see below). |
| **2** | If nothing listens on `http://127.0.0.1:11434`, starts bundled `ollama serve` in the background and waits up to **30 seconds** for readiness. If Ollama was already running, it is **not** stopped at the end. |
| **3** | Copies `ingest.py`, `mcp_server.py`, `domain_feeder.py`, `sanitizer.py`, and `concept_registry.json` (when present) into the bundle, then runs the bundle’s Python on `ingest.py` with the assembled arguments. |

On success it prints the VectorDB path. If it started Ollama itself, it stops that process in a cleanup handler; a pre-existing Ollama is left running.

---

## Command-line options

| Option | Description |
|--------|-------------|
| `--model NAME` | Ollama embedding model (default: `nomic-embed-text`). Ensure the model is pulled (`ollama pull …`). |
| `--mode MODE` | Ingestion mode (see **Modes** below). |
| `--domain NAME` | Logical domain label (default: `general`). |
| `--collection NAME` | Override Chroma collection name (optional). |
| `--rally-project NAME` | Rally mode: project name. |
| `--rally-filter EXPR` | Rally mode: filter expression. |
| `--confluence-space KEY` | Wiki/Confluence-related ingestion. |
| `--confluence-label LABEL` | Wiki/Confluence label filter. |
| `--repo NAME` | Subfolder under source or single-repo name (see **Repo handling**). |
| `--source PATH` | File or directory to ingest; overrides mode default folder when set. |
| `--db-path PATH` | Vector database directory (created if missing). Default: `<BaseDir>/VectorDB`. |
| `--workers N` | Embedding parallelism hints: sets `OLLAMA_NUM_PARALLEL` and `EMBED_WORKERS` (default: **2**). |
| `--mib-keep-deprecated` | Passes through to ingest for MIB ingestion. |
| `--dry-run` | Plan without writing vectors (ingest decides behavior). |
| `--force` | Force re-processing where ingest supports it. |
| `--clean-stale` | Remove stale index entries per ingest logic. |
| `--verbose` | Verbose ingest logging. |
| `-h`, `--help` | Print usage and exit. |

Unknown options exit with code **2**.

---

## Modes and default source folders

If you pass `--mode` and **do not** pass `--source`, and the mode is **not** `status`, `rally`, or `wiki`, the script picks a default folder under the portable base directory:

| Mode | Default folder under `<BaseDir>` |
|------|----------------------------------|
| `code` | `Codebase` |
| `domain`, `theory` | `DomainDocs` |
| `rfc` | `RFCs` |
| `mib` | `MIBs` |
| `community`, `customer` | `CommunityData` |
| `release-notes` | `Codebase` |
| *(any other mode not listed above)* | `Codebase` |

Modes `status`, `rally`, and `wiki` do **not** auto-set `--source` from this table; supply `--source` (or rely on ingest’s own defaults) as needed.

Always pass `--source` explicitly when your data lives outside the default tree.

---

## Source path (`--source`)

- Path must exist; otherwise the script exits with an error.
- Exported to the ingest process as **`SOURCE_FOLDER`** (absolute path).
- If `--mode` requires a source and `SOURCE_FOLDER` ends up empty (e.g. default folder missing), ingest may still run but without `--source` — prefer checking the script’s printed **Default source** line.

---

## Repo handling (`--repo`)

Resolved relative to the effective source directory (`SOURCE_FOLDER`, or `Codebase` under the base when source is unset):

- If `--repo` equals the **basename** of the source folder → **single-repo mode** (`REPO_NAME`).
- Else if `<source>/<repo>` is a directory → **subfolder filter** (`INGEST_REPO`).
- Else → **single-repo mode** with alias semantics (see script messages).

---

## Ollama and GPU

- **Models** live under `$BASE_DIR/Models` via `OLLAMA_MODELS`.
- **`OLLAMA_KEEP_ALIVE=-1`** keeps loaded models resident during the run.
- **`CUDA_VISIBLE_DEVICES`** defaults to `0` if unset.
- The script posts a small **embed warmup** for `--model`; if it fails, you may need `ollama pull <model>` while Ollama is running.

---

## Python interpreter

The script prefers, in order:

1. `<BaseDir>/Python/bin/python3`  
2. `<BaseDir>/Python/bin/python`  
3. `<BaseDir>/PyEnv/bin/python3`  

If none are executable, the script errors out.

---

## Exit codes

- **0** — Ingest completed successfully.  
- **1** — Missing portable layout, Ollama not ready in time, missing Python, missing `--source` path, or ingest failure.  
- **2** — Unknown CLI option.  

---

## Example commands

```bash
# Codebase index with default model
./run.sh --mode code

# Larger embedding model
./run.sh --mode code --model mxbai-embed-large

# Domain docs with explicit domain label
./run.sh --mode domain --domain nms --source "$PWD/Studio-Portable-RAG/DomainDocs"

# MIBs
./run.sh --mode mib --domain nms --source "$PWD/Studio-Portable-RAG/MIBs"

# Status / diagnostics only (no default source folder applied the same way as code)
./run.sh --mode status

# Custom VectorDB location
./run.sh --mode code --db-path /data/my-vectordb

# More parallel embed workers (tune to your GPU/CPU)
./run.sh --mode code --workers 4
```

(Adjust paths if your bundle directory name differs.)

---

## Troubleshooting

| Symptom | What to check |
|---------|----------------|
| `Portable RAG not found` | Run `./build.sh`; confirm `Studio-Portable-RAG/Ollama/ollama` exists and is executable. |
| `Ollama did not become ready within 30 seconds` | Port 11434 blocked, firewall, or another broken Ollama instance; try `curl -s http://127.0.0.1:11434/`. |
| Embed warmup skipped | Pull the model: `ollama pull nomic-embed-text` (or your `--model`). |
| Wrong files ingested | Set `--source` explicitly; verify **Mode** → default folder table. |
| `ingest.py failed` | Run the same command with `--verbose`; inspect ingest logs and checkpoint files under your `DB_PATH`. |

---

## Related files

| File | Role |
|------|------|
| `build.sh` | Produces the portable tree `run.sh` expects. |
| `ingest.py` | Actual chunking, embedding, and Chroma writes. |
| `run.ps1` | Windows equivalent runner. |
| `mcp_server.py` | MCP server (copied into bundle for parity; not started by `run.sh`). |
