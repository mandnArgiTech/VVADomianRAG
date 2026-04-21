#!/usr/bin/env bash
# Start FastAPI bridge on :8000, then Vite on :5180 (same as two terminals: npm run bridge + npm run demo:kernel).
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"
export PYTHONPATH="${PYTHONPATH:-$DIR/../python}"
if ! command -v uvicorn >/dev/null 2>&1; then
  echo "Install: pip install -r $DIR/requirements-bridge.txt" >&2
  exit 1
fi
uvicorn bridge_server:app --host 127.0.0.1 --port 8000 &
UV_PID=$!
cleanup() { kill "$UV_PID" 2>/dev/null || true; }
trap cleanup EXIT INT TERM
# Wait for bridge to accept connections (avoids Vite proxy ECONNREFUSED storm).
for _ in $(seq 1 50); do
  if bash -c "echo >/dev/tcp/127.0.0.1/8000" 2>/dev/null; then break; fi
  sleep 0.1
done
exec npx vite --config standalone/vite.kernel.config.ts
