"""Concurrent aiohttp embedding against Ollama (lazy-bound to ``ingest`` runtime globals)."""

from __future__ import annotations

import asyncio
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

try:
    from tqdm.asyncio import tqdm as tqdm_asyncio
except ImportError:  # pragma: no cover
    tqdm_asyncio = None


async def _async_http_embed_batch(
    session: Any, model: str, texts: List[str], timeout: float = 300.0
) -> List[List[float]]:
    import ingest as ing

    if ing.aiohttp is None:
        raise RuntimeError("aiohttp is not installed")
    if session is None:
        raise TypeError("aiohttp ClientSession is required (got None)")
    url = ing._ollama_embed_url()
    to = ing.aiohttp.ClientTimeout(total=timeout)
    async with session.post(url, json={"model": model, "input": texts}, timeout=to) as resp:
        resp.raise_for_status()
        data = await resp.json()
    embs = data.get("embeddings")
    if embs is not None:
        return embs
    one = data.get("embedding")
    if one is not None:
        return [one]
    raise RuntimeError(f"Unexpected Ollama embed response: {list(data.keys())}")


async def embed_with_retry_http_async(
    session: Any,
    model: str,
    batch: List[str],
    async_lock: Optional[asyncio.Lock],
) -> Optional[List[List[float]]]:
    import ingest as ing

    MAX_RETRIES = ing.MAX_RETRIES
    EMBED_BACKOFF_SEC = ing.EMBED_BACKOFF_SEC
    logger = ing.logger

    async def _try(b: List[str]) -> Optional[List[List[float]]]:
        for _ in range(MAX_RETRIES):
            try:
                if async_lock is not None:
                    async with async_lock:
                        return await ing._async_http_embed_batch(session, model, b)
                return await ing._async_http_embed_batch(session, model, b)
            except Exception as exc:
                logger.warning("embed async retry: %s", exc)
                await asyncio.sleep(EMBED_BACKOFF_SEC)
        if len(b) <= 1:
            return None
        mid = max(1, len(b) // 2)
        a = await _try(b[:mid])
        b2 = await _try(b[mid:])
        if a is None or b2 is None:
            return None
        return a + b2

    return await _try(batch)


async def run_async_embedding_batches(
    batches: List[List[Tuple[str, str, Dict[str, str]]]],
    embed_model: str,
    concurrency: int,
) -> List[Optional[Tuple[List[str], List[str], List[Dict[str, str]], List[List[float]]]]]:
    """Concurrent aiohttp embedding; returns one result per input batch (order preserved)."""
    import ingest as ing

    if ing.aiohttp is None:
        return [None] * len(batches)
    sem = asyncio.Semaphore(concurrency)
    alock = asyncio.Lock() if ing._embed_serialize_on() else None

    async with ing.aiohttp.ClientSession() as session:

        async def one(
            batch: List[Tuple[str, str, Dict[str, str]]],
        ) -> Optional[Tuple[List[str], List[str], List[Dict[str, str]], List[List[float]]]]:
            async with sem:
                ids, texts, metas = [], [], []
                for cid, text, meta in batch:
                    ids.append(cid)
                    texts.append(text)
                    metas.append(meta)
                vecs = await ing.embed_with_retry_http_async(session, embed_model, texts, alock)
                if vecs is None:
                    return None
                return (ids, texts, metas, vecs)

        coros = [one(b) for b in batches]
        if tqdm_asyncio is not None:
            g_kw: Dict[str, Any] = {"desc": "Embedding", "unit": "batch"}
            if not sys.stdout.isatty():
                g_kw["mininterval"] = float(os.environ.get("INGEST_TQDM_MININTERVAL", "2.0"))
            return list(await tqdm_asyncio.gather(*coros, **g_kw))
        return list(await asyncio.gather(*coros))
