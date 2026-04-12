#!/usr/bin/env bash
# Linux counterpart to build.ps1 — portable-ish layout under Studio-Portable-RAG/
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(cd "$SCRIPT_DIR" && pwd)/Studio-Portable-RAG"
mkdir -p "$BASE_DIR"
BASE_DIR="$(cd "$BASE_DIR" && pwd)"

echo ""
echo " Building Universal Domain RAG (Linux layout)..."
echo " BaseDir (absolute): $BASE_DIR"
echo ""

die() { echo "[ERROR] $*" >&2; exit 1; }

need_cmd() { command -v "$1" >/dev/null 2>&1 || die "Missing required command: $1"; }

expand_zst_tar() {
  local archive="$1" dest="$2"
  mkdir -p "$dest"
  if tar --help 2>&1 | grep -q -- '--zstd'; then
    tar --zstd -xf "$archive" -C "$dest"
  elif command -v zstd >/dev/null 2>&1; then
    zstd -dc "$archive" | tar -xf - -C "$dest"
  else
    die "Need GNU tar with --zstd or the zstd binary to extract Ollama archives."
  fi
}

# Pre-downloaded archive next to this script (same idea as build.ps1)
get_archive() {
  local filename="$1" url="$2" temp_dest="$3"
  local local_path="$SCRIPT_DIR/$filename"
  if [[ -f "$local_path" ]]; then
    echo "      Pre-downloaded file found: $filename (skipping download)" >&2
    echo "$local_path"
    return 0
  fi
  echo "      Downloading $filename..." >&2
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL -o "$temp_dest" "$url"
  elif command -v wget >/dev/null 2>&1; then
    wget -q -O "$temp_dest" "$url"
  else
    die "Need curl or wget to download $filename"
  fi
  echo "$temp_dest"
}

ollama_asset_name() {
  case "$(uname -m)" in
    x86_64)  echo "ollama-linux-amd64.tar.zst" ;;
    aarch64) echo "ollama-linux-arm64.tar.zst" ;;
    *) die "Unsupported architecture: $(uname -m) (need x86_64 or aarch64)" ;;
  esac
}

ollama_download_url() {
  local name="$1"
  python3 - "$name" <<'PY'
import json, sys, urllib.request
name = sys.argv[1]
url = "https://api.github.com/repos/ollama/ollama/releases/latest"
req = urllib.request.Request(url, headers={"User-Agent": "DomainRAG-build"})
with urllib.request.urlopen(req, timeout=120) as r:
    data = json.load(r)
for a in data.get("assets", []):
    if a.get("name") == name:
        print(a["browser_download_url"])
        raise SystemExit(0)
raise SystemExit(f"Asset not found in latest release: {name}")
PY
}

echo "[GPU] Checking for NVIDIA GPU..."
if command -v nvidia-smi >/dev/null 2>&1; then
  if gpu_info="$(nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>/dev/null)"; then
    [[ -n "$gpu_info" ]] && echo "      GPU detected: $gpu_info" || echo "      WARNING: nvidia-smi returned no output. Ingestion may run on CPU."
  else
    echo "      WARNING: nvidia-smi failed. Ingestion may run on CPU."
  fi
else
  echo "      WARNING: nvidia-smi not found. Ingestion may run on CPU."
fi

need_cmd python3
need_cmd tar

python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' \
  || die "Python 3.10 or newer is required (found: $(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')')"

mkdir -p "$BASE_DIR/Ollama" "$BASE_DIR/Python" "$BASE_DIR/Models" "$BASE_DIR/Codebase" \
  "$BASE_DIR/VectorDB" "$BASE_DIR/DomainDocs" "$BASE_DIR/RFCs" "$BASE_DIR/MIBs" \
  "$BASE_DIR/CommunityData"

# --- Portable Ollama ---
echo "[1/7] Setting up Ollama (Linux binary from GitHub releases)..."
OLLAMA_NAME="$(ollama_asset_name)"
OLLAMA_URL="$(ollama_download_url "$OLLAMA_NAME")"
TEMP_ZST="$BASE_DIR/ollama-download.tar.zst"
ARCHIVE_PATH="$(get_archive "$OLLAMA_NAME" "$OLLAMA_URL" "$TEMP_ZST")"
TMP_EXTRACT="$(mktemp -d)"
cleanup_extract() { rm -rf "$TMP_EXTRACT"; }
trap cleanup_extract EXIT
expand_zst_tar "$ARCHIVE_PATH" "$TMP_EXTRACT"
OLLAMA_BIN_SRC="$(find "$TMP_EXTRACT" -type f -name ollama -print -quit)"
[[ -n "$OLLAMA_BIN_SRC" ]] || die "Could not find ollama binary inside archive"
install -m 755 "$OLLAMA_BIN_SRC" "$BASE_DIR/Ollama/ollama"
trap - EXIT
rm -rf "$TMP_EXTRACT"
[[ "$ARCHIVE_PATH" == "$TEMP_ZST" ]] && rm -f "$TEMP_ZST"

# --- Python venv (Linux equivalent of embedded Python on Windows) ---
echo "[2/7] Creating Python virtualenv and upgrading pip..."
if [[ ! -x "$BASE_DIR/Python/bin/python3" ]]; then
  python3 -m venv "$BASE_DIR/Python"
fi
PIP=( "$BASE_DIR/Python/bin/pip" )
"${PIP[@]}" install -q --upgrade pip

echo "[3/7] Installing Python dependencies..."
REQ="$SCRIPT_DIR/requirements.txt"
[[ -f "$REQ" ]] || die "Missing requirements.txt next to build.sh"
"${PIP[@]}" install -r "$REQ"
"${PIP[@]}" install tree-sitter tree-sitter-c tree-sitter-cpp tree-sitter-java
if command -v git >/dev/null 2>&1; then
  "${PIP[@]}" install "git+https://github.com/6cdh/tree-sitter-scheme.git@c6cb7c7d7a04b3f5d999c28e2e9c0c31b2d50ece"
else
  echo "      git not found — skipping tree-sitter-scheme (Scheme chunking will use regex fallback)" >&2
fi

# --- Pull Ollama models (embeddings + small Qwen LLMs for enrich / local chat) ---
echo "[4/7] Downloading Ollama models..."
export OLLAMA_MODELS="$BASE_DIR/Models"
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
export OLLAMA_KEEP_ALIVE="-1"

OLLAMA_PROC=""
if curl -sf "http://127.0.0.1:11434/" >/dev/null 2>&1; then
  echo "    Reusing existing Ollama on :11434"
else
  echo "    Starting bundled Ollama..."
  "$BASE_DIR/Ollama/ollama" serve >/dev/null 2>&1 &
  OLLAMA_PROC=$!
  for _ in $(seq 1 30); do
    curl -sf "http://127.0.0.1:11434/" >/dev/null 2>&1 && break
    sleep 1
  done
  curl -sf "http://127.0.0.1:11434/" >/dev/null 2>&1 || {
    [[ -n "$OLLAMA_PROC" ]] && kill "$OLLAMA_PROC" 2>/dev/null || true
    die "Ollama did not start within 30 seconds."
  }
fi

echo "    Pulling nomic-embed-text..."
"$BASE_DIR/Ollama/ollama" pull nomic-embed-text
echo "    Pulling mxbai-embed-large..."
"$BASE_DIR/Ollama/ollama" pull mxbai-embed-large
echo "    Pulling qwen2.5:0.5b (ingest --enrich-metadata default / tiny LLM)..."
"$BASE_DIR/Ollama/ollama" pull qwen2.5:0.5b
echo "    Pulling qwen2.5:3b (small general LLM)..."
"$BASE_DIR/Ollama/ollama" pull qwen2.5:3b

if [[ -n "${OLLAMA_PROC:-}" ]]; then
  kill "$OLLAMA_PROC" 2>/dev/null || true
  wait "$OLLAMA_PROC" 2>/dev/null || true
fi

echo "[5/7] Copying scripts and support files..."
cp -f "$SCRIPT_DIR/ingest.py" "$BASE_DIR/ingest.py"
cp -f "$SCRIPT_DIR/mcp_server.py" "$BASE_DIR/mcp_server.py"
cp -f "$SCRIPT_DIR/domain_feeder.py" "$BASE_DIR/domain_feeder.py"
cp -f "$SCRIPT_DIR/hybrid_search.py" "$BASE_DIR/hybrid_search.py"
cp -f "$SCRIPT_DIR/query.py" "$BASE_DIR/query.py"
cp -f "$SCRIPT_DIR/gui_backend.py" "$BASE_DIR/gui_backend.py"
cp -f "$SCRIPT_DIR/agent_tools.py" "$BASE_DIR/agent_tools.py"
[[ -f "$SCRIPT_DIR/index.html" ]] && cp -f "$SCRIPT_DIR/index.html" "$BASE_DIR/index.html" || true
if [[ -d "$SCRIPT_DIR/static" ]]; then
  mkdir -p "$BASE_DIR/static"
  cp -a "$SCRIPT_DIR/static/." "$BASE_DIR/static/"
fi
if [[ -d "$SCRIPT_DIR/util" ]]; then
  mkdir -p "$BASE_DIR/util"
  cp -a "$SCRIPT_DIR/util/." "$BASE_DIR/util/"
fi
[[ -f "$SCRIPT_DIR/sanitizer.py" ]] && cp -f "$SCRIPT_DIR/sanitizer.py" "$BASE_DIR/sanitizer.py" || true
[[ -f "$SCRIPT_DIR/concept_registry.json" ]] && cp -f "$SCRIPT_DIR/concept_registry.json" "$BASE_DIR/concept_registry.json" || true

PY="$BASE_DIR/Python/bin/python3"
echo "[6/7] Post-install validation..."
(
  cd "$BASE_DIR"
  "$PY" -c "import langchain_chroma, chromadb, tqdm; print('core deps: OK')"
  "$PY" -c "import hybrid_search; print('hybrid_search: OK')"
  "$PY" -c "import gui_backend; print('gui_backend: OK')"
  "$PY" -c "import tree_sitter; print('tree-sitter: OK')" 2>/dev/null || echo "      tree-sitter optional import failed (C/C++/Java AST will fall back)."
  "$PY" -c "import tree_sitter_scheme; print('tree-sitter-scheme: OK')" 2>/dev/null || echo "      tree-sitter-scheme import failed (Scheme chunking will use regex fallback)."
)

echo "[6b/7] Downloading frontend assets (Split.js)..."
mkdir -p "$SCRIPT_DIR/static"
if command -v curl >/dev/null 2>&1; then
  curl -fsSL "https://cdnjs.cloudflare.com/ajax/libs/split.js/1.6.5/split.min.js" \
    -o "$SCRIPT_DIR/static/split.min.js" \
    || echo "      WARNING: could not download split.min.js (offline?). Using existing if present."
elif command -v wget >/dev/null 2>&1; then
  wget -q -O "$SCRIPT_DIR/static/split.min.js" \
    "https://cdnjs.cloudflare.com/ajax/libs/split.js/1.6.5/split.min.js" \
    || echo "      WARNING: could not download split.min.js (offline?). Using existing if present."
fi

echo "[7/7] Merging ~/.cursor/mcp.json..."
export DOMAIN_RAG_MCP_BASE="$BASE_DIR"
python3 <<'PYMERGE'
import json, os
from pathlib import Path

base = Path(os.environ["DOMAIN_RAG_MCP_BASE"]).resolve()
cursor_dir = Path.home() / ".cursor"
cursor_dir.mkdir(parents=True, exist_ok=True)
mcp_path = cursor_dir / "mcp.json"

py = str(base / "Python" / "bin" / "python3")
if not Path(py).is_file():
    py = str(base / "Python" / "bin" / "python")

entry = {
    "command": py,
    "args": [str(base / "mcp_server.py")],
    "env": {
        "OLLAMA_MODELS": str(base / "Models"),
        "OLLAMA_EXE": str(base / "Ollama" / "ollama"),
        "DB_PATH": str(base / "VectorDB"),
        "MCP_LOG": str(base / "mcp_server.log"),
        "CUDA_VISIBLE_DEVICES": "0",
        "OLLAMA_KEEP_ALIVE": "-1",
    },
}

server_map = {}
if mcp_path.is_file():
    try:
        old = json.loads(mcp_path.read_text(encoding="utf-8"))
        for name, val in (old.get("mcpServers") or {}).items():
            if name == "codebase-rag":
                continue
            server_map[name] = val
    except json.JSONDecodeError:
        bak = mcp_path.with_name("mcp.json.bak")
        bak.write_text(mcp_path.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"      WARNING: existing mcp.json malformed; backed up to {bak}")

server_map["codebase-rag"] = entry
out = {"mcpServers": server_map}
mcp_path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
print(f"         Written: {mcp_path}")
PYMERGE

echo "****************************************************************"
echo "* Build complete. RAG layout is ready.                         *"
echo "****************************************************************"
echo "* Multi-repo layout (recommended):                             *"
echo "*   Studio-Portable-RAG/Codebase/<repo-name>/                  *"
echo "****************************************************************"
echo "* Code ingest:    ./run.sh --mode code                         *"
echo "* Domain docs:    ./run.sh --mode domain --domain nms          *"
echo "* Status:         ./run.sh --mode status                       *"
echo "* GPU model:      ./run.sh --model mxbai-embed-large           *"
echo "* Query CLI:      ./query.sh semantic \"your question\"         *"
echo "* Web dashboard:  ./gui.sh (http://127.0.0.1:8501/)            *"
echo "****************************************************************"
