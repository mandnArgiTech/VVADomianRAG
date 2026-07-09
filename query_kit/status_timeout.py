"""Vector DB status summary and cross-platform timeouts for sync search."""

from __future__ import annotations

import threading
from collections import Counter
from typing import Any, Callable, Dict, List

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
    """Run ``fn`` with a wall-clock timeout; raise ``TimeoutError`` on expiry.

    Uses a worker thread instead of ``signal.SIGALRM``: SIGALRM was a no-op on
    Windows, raised ``ValueError`` when called from a non-main thread (e.g. the
    GUI backend's thread pool), and could not interrupt blocking C-level I/O
    inside Chroma/SQLite/Ollama anyway. The worker thread is a daemon, so a
    truly stuck call no longer blocks the caller (it is abandoned on timeout).
    """
    if seconds <= 0:
        return fn(*args, **kwargs)

    holder: Dict[str, Any] = {}

    def _run() -> None:
        try:
            holder["result"] = fn(*args, **kwargs)
        except BaseException as exc:  # propagate KeyboardInterrupt etc. to caller
            holder["error"] = exc

    t = threading.Thread(target=_run, daemon=True, name="rag-query-timeout")
    t.start()
    t.join(timeout=max(1, int(seconds)))
    if t.is_alive():
        raise TimeoutError(f"Query timed out after {seconds}s")
    if "error" in holder:
        raise holder["error"]
    return holder.get("result")
