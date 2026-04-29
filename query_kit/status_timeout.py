"""Vector DB status summary and SIGALRM timeouts for sync search."""

from __future__ import annotations

import logging
import signal
from collections import Counter
from typing import Any, Callable, List

from util.chroma_client import persistent_chroma_client as _persistent_chroma_client
from util.chroma_client import safe_collection_count as _safe_count_util

from query_kit.concepts import concept_parts


def safe_collection_count(coll: Any) -> int:
    return _safe_count_util(coll)


def run_status(db_path: str) -> str:
    lines: List[str] = []
    lines.append("=" * 64)
    lines.append("            DOMAIN RAG — KNOWLEDGE BASE STATUS")
    lines.append("=" * 64)
    client = _persistent_chroma_client(db_path)
    cols = client.list_collections()
    concept_counts: Counter[str] = Counter()
    rows = []
    for c in sorted(cols, key=lambda x: x.name):
        coll = client.get_collection(c.name)
        n = safe_collection_count(coll)
        if n == 0:
            rows.append((c.name, 0, 0, ""))
            continue
        sample = coll.get(include=["metadatas"], limit=min(n, 8000))
        metas = sample.get("metadatas") or []
        sources = {str(m.get("source", "")) for m in metas if m}
        for m in metas:
            if not m:
                continue
            cs = m.get("concepts", "")
            if cs:
                for part in concept_parts(str(cs)):
                    concept_counts[part] += 1
        dates = [str(m.get("ingestion_date", "")) for m in metas if m and m.get("ingestion_date")]
        last_ing = max(dates) if dates else ""
        rows.append((c.name, n, len(sources), last_ing))
    hdr = f"{'Collection':<22} {'Chunks':>8} {'Sources':>8} {'Last Ingested':<22}"
    lines.append(hdr)
    lines.append("-" * 64)
    for name, n, sc, li in rows:
        lines.append(f"{name:<22} {n:>8,} {sc:>8} {li:<22}")
    lines.append("=" * 64)
    top = concept_counts.most_common(15)
    if top:
        lines.append("Top concepts: " + ", ".join(f"{k}({v})" for k, v in top))
    return "\n".join(lines)


def run_with_timeout(seconds: int, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    if seconds <= 0:
        return fn(*args, **kwargs)
    if not hasattr(signal, "SIGALRM"):
        return fn(*args, **kwargs)

    def handler(_signum: Any, _frame: Any) -> None:
        raise TimeoutError(f"Query timed out after {seconds}s")

    old = signal.signal(signal.SIGALRM, handler)
    try:
        signal.alarm(max(1, int(seconds)))
        return fn(*args, **kwargs)
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)
