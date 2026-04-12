#!/usr/bin/env bash
# Enterprise dashboard: sync UI assets into Studio-Portable-RAG, start Ollama if needed, run uvicorn.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${RAG_GUI_PORT:-8501}"

BASE_DIR="$(cd "$SCRIPT_DIR/Studio-Portable-RAG" 2>/dev/null && pwd)" || BASE_DIR=""
if [[ ! -x "${BASE_DIR:-}/Ollama/ollama" ]]; then
  alt="$(cd "$SCRIPT_DIR/Portable_RAG" 2>/dev/null && pwd)" || alt=""
  if [[ -n "$alt" && -x "$alt/Ollama/ollama" ]]; then
    BASE_DIR="$alt"
  fi
fi

if [[ -z "$BASE_DIR" || ! -x "$BASE_DIR/Ollama/ollama" ]]; then
  echo "[ERROR] Portable RAG not found. Run ./build.sh first." >&2
  exit 1
fi

sync_gui_assets() {
  cp -f "$SCRIPT_DIR/gui_backend.py" "$BASE_DIR/gui_backend.py"
  cp -f "$SCRIPT_DIR/agent_tools.py" "$BASE_DIR/agent_tools.py"
  cp -f "$SCRIPT_DIR/query.py" "$BASE_DIR/query.py"
  cp -f "$SCRIPT_DIR/hybrid_search.py" "$BASE_DIR/hybrid_search.py"
  cp -f "$SCRIPT_DIR/ingest.py" "$BASE_DIR/ingest.py"
  [[ -f "$SCRIPT_DIR/index.html" ]] && cp -f "$SCRIPT_DIR/index.html" "$BASE_DIR/index.html"
  if [[ -d "$SCRIPT_DIR/static" ]]; then
    mkdir -p "$BASE_DIR/static"
    cp -a "$SCRIPT_DIR/static/." "$BASE_DIR/static/"
  fi
  if [[ -d "$SCRIPT_DIR/util" ]]; then
    mkdir -p "$BASE_DIR/util"
    cp -a "$SCRIPT_DIR/util/." "$BASE_DIR/util/"
  fi
}

sync_gui_assets

PYTHON_EXE="$BASE_DIR/Python/bin/python3"
[[ -x "$PYTHON_EXE" ]] || PYTHON_EXE="$BASE_DIR/Python/bin/python"
[[ -x "$PYTHON_EXE" ]] || PYTHON_EXE="$BASE_DIR/PyEnv/bin/python3"
[[ -x "$PYTHON_EXE" ]] || { echo "[ERROR] Python not found under $BASE_DIR/Python" >&2; exit 1; }

export OLLAMA_MODELS="${OLLAMA_MODELS:-$BASE_DIR/Models}"
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
export OLLAMA_KEEP_ALIVE="${OLLAMA_KEEP_ALIVE:--1}"
export EMBEDDING_MODEL="${EMBEDDING_MODEL:-mxbai-embed-large}"

EMBED_MODEL="$EMBEDDING_MODEL"
OLLAMA_BIN="$BASE_DIR/Ollama/ollama"
OLLAMA_PROC=""
OLLAMA_ALREADY=0

echo "[GUI] Starting / reusing Ollama (needed for ingest embeddings & chat)..."
if curl -sf "http://127.0.0.1:11434/" >/dev/null 2>&1; then
  OLLAMA_ALREADY=1
  echo "            Existing Ollama on :11434 — reusing."
else
  "$OLLAMA_BIN" serve >/dev/null 2>&1 &
  OLLAMA_PROC=$!
  echo "            Waiting for http://127.0.0.1:11434 (max 30s)..."
  ready=0
  for _ in $(seq 1 30); do
    if curl -sf "http://127.0.0.1:11434/" >/dev/null 2>&1; then
      ready=1
      break
    fi
    sleep 1
  done
  if [[ "$ready" -ne 1 ]]; then
    [[ -n "$OLLAMA_PROC" ]] && kill "$OLLAMA_PROC" 2>/dev/null || true
    echo "[ERROR] Ollama did not become ready within 30 seconds." >&2
    exit 1
  fi
  echo "            Ollama is ready."
fi

echo "            Embed warmup: $EMBED_MODEL"
curl -sf -X POST "http://127.0.0.1:11434/api/embed" \
  -H "Content-Type: application/json" \
  -d "{\"model\": \"$EMBED_MODEL\", \"input\": \"warmup\"}" >/dev/null 2>&1 \
  || echo "            (warmup skipped — run: ollama pull $EMBED_MODEL)" >&2

cleanup_ollama() {
  if [[ "$OLLAMA_ALREADY" -eq 1 ]]; then
    echo "Ollama left running (was already active before the dashboard started)." >&2
  elif [[ -n "${OLLAMA_PROC:-}" ]]; then
    echo "Shutting down Ollama server (started by gui.sh)..." >&2
    kill "$OLLAMA_PROC" 2>/dev/null || true
    wait "$OLLAMA_PROC" 2>/dev/null || true
  fi
}

trap cleanup_ollama EXIT

echo "Dashboard: http://127.0.0.1:${PORT}/"
echo "Working dir: $BASE_DIR (Ctrl+C to stop; Ollama stops too if gui.sh started it)"
cd "$BASE_DIR"
"$PYTHON_EXE" -m uvicorn gui_backend:app --host 127.0.0.1 --port "$PORT"
