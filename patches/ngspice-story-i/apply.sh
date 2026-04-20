#!/bin/sh
# Apply Story I diagnostic hooks on top of the ngspice submodule (git am).
set -e
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
NG="$ROOT/Studio-Portable-RAG/Codebase/ngspice"
PATCH="$ROOT/patches/ngspice-story-i/0001-Add-optional-NGSPICE_DIAG_FILE-JSON-Lines-diagnostic.patch"
test -f "$PATCH"
cd "$NG"
git am "$PATCH"
echo "Applied Story I patch. Rebuild: cd \"$NG\" && make -j\$(nproc)"
