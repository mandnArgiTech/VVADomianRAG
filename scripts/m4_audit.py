#!/usr/bin/env python3
"""M4-A audit from docs/stories/STORY_M4_verify_commit.md — run from repo root."""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import os

os.chdir(ROOT)

files_all = [
    "query.py",
    "mcp_server.py",
    "ingest.py",
    "gui_backend.py",
    "agent_tools.py",
    "util/__init__.py",
    "util/constants.py",
    "util/chroma_client.py",
    "util/formatting.py",
    "util/chunk_metadata.py",
    "util/search_primitives.py",
]

# 1. Syntax check
print("=== Syntax ===")
ok = True
for f in files_all:
    try:
        ast.parse((ROOT / f).read_text(encoding="utf-8"))
        print(f"  OK  {f}")
    except SyntaxError as e:
        print(f"  ERR {f}: {e}")
        ok = False
if not ok:
    sys.exit(1)

# 2. No cross-file duplicate function/class BODIES remain
print("\n=== Cross-file duplicate bodies ===")
SKIP = {"main", "__init__", "show", "event_stream", "_safe_count"}
all_fns: dict[str, list[str]] = {}
for f in ["query.py", "mcp_server.py", "ingest.py", "gui_backend.py"]:
    src = (ROOT / f).read_text(encoding="utf-8")
    for m in re.finditer(r"^(?:def |async def |class )(\w+)", src, re.MULTILINE):
        name = m.group(1)
        if name not in SKIP:
            all_fns.setdefault(name, []).append(f)
dups = {k: v for k, v in all_fns.items() if len(v) > 1}
intentional = {
    "_sync_multi_search",
    "_sync_multi_search_with_dependency_hop",
    "_sync_fetch_dependents",
    "_sync_fetch_callers",
    "connect_chroma_with_retry",
    "_default_vector_db_dir",
}
unexpected = {k: v for k, v in dups.items() if k not in intentional}
if unexpected:
    for name, locs in sorted(unexpected.items()):
        print(f"  UNINTENTIONAL DUP: {name} in {locs}")
    sys.exit(1)
else:
    print("  OK — only intentional dups remain")

# 3. No dead comment aliases left
print("\n=== Dead comment aliases ===")
for f in ["query.py", "mcp_server.py"]:
    src = (ROOT / f).read_text(encoding="utf-8")
    dead = re.findall(r"#\s*\w+ →.*util\.\w+.*imported", src)
    if dead:
        print(f"  DEAD in {f}: {dead}")
    else:
        print(f"  OK  {f}")

# 4. Util modules have no circular imports
print("\n=== No circular imports in util ===")
for f in [
    "util/constants.py",
    "util/chroma_client.py",
    "util/formatting.py",
    "util/chunk_metadata.py",
    "util/search_primitives.py",
]:
    src = (ROOT / f).read_text(encoding="utf-8")
    bad = re.findall(
        r"^(?:from|import)\s+(query|mcp_server|ingest|gui_backend)\b", src, re.MULTILINE
    )
    if bad:
        print(f"  CIRCULAR in {f}: imports {bad}")
    else:
        print(f"  OK  {f}")

print("\nAll checks passed.")
