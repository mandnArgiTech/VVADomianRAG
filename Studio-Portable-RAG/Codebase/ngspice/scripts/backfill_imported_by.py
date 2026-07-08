#!/usr/bin/env python3
"""
Backfill imported_by / imported_by_count from c_includes_internal in rag_index.json.

When run as __main__, loads ../rag_index.json, applies backfill, writes atomically.
upgrade_rag_index.py imports backfill_imported_by_only() as part of the full pipeline.
"""
from __future__ import annotations

import json
import os
import tempfile
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RAG_PATH = REPO_ROOT / "rag_index.json"


def backfill_imported_by_only(files: list[dict]) -> None:
    rev: dict[str, list[str]] = defaultdict(list)
    for ent in files:
        p = ent["path"]
        for inc in ent.get("c_includes_internal") or []:
            rev[inc].append(p)
    for ent in files:
        p = ent["path"]
        lst = sorted(set(rev.get(p, [])))
        ent["imported_by"] = lst
        ent["imported_by_count"] = len(lst)


def main() -> None:
    data = json.loads(RAG_PATH.read_text(encoding="utf-8"))
    backfill_imported_by_only(data["files"])
    out = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    fd, tmp = tempfile.mkstemp(dir=str(RAG_PATH.parent), suffix=".json.tmp")
    os.close(fd)
    tmp_path = Path(tmp)
    try:
        tmp_path.write_text(out, encoding="utf-8")
        os.replace(tmp, RAG_PATH)
    except OSError:
        tmp_path.unlink(missing_ok=True)
        raise
    print(f"Wrote {RAG_PATH} (imported_by backfill only).")


if __name__ == "__main__":
    main()
