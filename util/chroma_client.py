"""
util/chroma_client.py — Chroma connection, collection discovery, embedding detection.

Previously duplicated across query.py and mcp_server.py.  Both files import
from here; neither carries its own copy any longer.

Public API
----------
DIM_TO_MODEL                    dict[int, str]  (re-exported from util.constants)
detect_embedding_model(db_path) str
embedding_model_from_db_path(db_path) str
persistent_chroma_client(path)  chromadb.PersistentClient
discover_collections(...)       Dict[str, Chroma]
connect_chroma_with_retry(...)  Tuple[PersistentClient, OllamaEmbeddings, Dict[str, Chroma]]
safe_collection_count(coll)     int
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, Optional, Tuple

import chromadb
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings

from util.constants import DIM_TO_MODEL

__all__ = [
    "DIM_TO_MODEL",
    "detect_embedding_model",
    "embedding_model_from_db_path",
    "persistent_chroma_client",
    "discover_collections",
    "connect_chroma_with_retry",
    "safe_collection_count",
]

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Low-level Chroma client
# ---------------------------------------------------------------------------

def persistent_chroma_client(path: str) -> chromadb.PersistentClient:
    """Return a PersistentClient with telemetry disabled (production hygiene)."""
    try:
        from chromadb.config import Settings  # type: ignore[import-untyped]

        return chromadb.PersistentClient(
            path=path,
            settings=Settings(anonymized_telemetry=False),
        )
    except Exception:
        return chromadb.PersistentClient(path=path)


# ---------------------------------------------------------------------------
# Embedding model detection
# ---------------------------------------------------------------------------

def embedding_model_from_db_path(db_path: str) -> str:
    """Resolve embedding model from on-disk DB config or Chroma dimension probe.

    Does NOT check the ``EMBEDDING_MODEL`` env var — use this when the caller
    must match an existing VectorDB exactly (e.g. ingestion paths).
    """
    config_path = os.path.join(db_path, "ingestion_config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, encoding="utf-8") as fh:
                model = json.load(fh).get("embedding_model", "")
            if model:
                return str(model).strip()
        except Exception:
            pass
    try:
        client = persistent_chroma_client(db_path)
        cols = client.list_collections()
        if cols:
            col = client.get_collection(cols[0].name)
            rows = col.get(limit=1, include=["embeddings"])
            embs = rows.get("embeddings")
            if embs is not None and len(embs) > 0 and len(embs[0]) > 0:
                dim = len(embs[0])
                if dim in DIM_TO_MODEL:
                    return DIM_TO_MODEL[dim]
    except Exception:
        pass
    return "nomic-embed-text"


def detect_embedding_model(db_path: str) -> str:
    """Resolve embedding model, honouring ``EMBEDDING_MODEL`` env override first."""
    env_val = os.environ.get("EMBEDDING_MODEL", "").strip()
    if env_val:
        return env_val
    return embedding_model_from_db_path(db_path)


# ---------------------------------------------------------------------------
# Collection discovery
# ---------------------------------------------------------------------------

def discover_collections(
    db_path: str,
    embeddings: OllamaEmbeddings,
    chroma_client: Optional[chromadb.PersistentClient] = None,
) -> Dict[str, Chroma]:
    """Open one PersistentClient and attach LangChain Chroma stores per collection.

    Reuses *chroma_client* for every ``Chroma`` wrapper (avoids a second sqlite
    open) and uses ``create_collection_if_not_exists=False`` so we only bind to
    existing collections — the default ``get_or_create`` path can misbehave
    across Chroma / LangChain versions when a DB already contains data.
    """
    out: Dict[str, Chroma] = {}
    try:
        client = chroma_client or persistent_chroma_client(db_path)
        infos = client.list_collections()
    except Exception as exc:
        log.error("discover_collections: list_collections failed for %s: %s", db_path, exc)
        return out
    if not infos:
        log.warning(
            "discover_collections: list_collections() returned no collections for %s "
            "(folder may be empty or DB is locked by another process).",
            db_path,
        )
        return out
    for info in infos:
        name = info.name
        try:
            out[name] = Chroma(
                client=client,
                collection_name=name,
                embedding_function=embeddings,
                create_collection_if_not_exists=False,
            )
        except Exception as exc:
            log.error("discover_collections: failed to open collection %r: %s", name, exc)
    return out


# ---------------------------------------------------------------------------
# Retry-wrapped connection
# ---------------------------------------------------------------------------

def connect_chroma_with_retry(
    db_path: str,
    model: str,
    *,
    retries: int = 3,
    delay: float = 2.0,
    shared_client: Optional[chromadb.PersistentClient] = None,
    shared_embedder: Optional[OllamaEmbeddings] = None,
) -> Tuple[chromadb.PersistentClient, OllamaEmbeddings, Dict[str, Chroma]]:
    """Connect to ChromaDB with retry logic.

    Parameters
    ----------
    db_path:
        Path to the ChromaDB persistence directory.
    model:
        Ollama embedding model name (used when *shared_embedder* is None).
    retries:
        Number of attempts before raising.
    delay:
        Seconds to wait between attempts.
    shared_client / shared_embedder:
        Pass existing singletons to avoid re-opening the DB or re-creating the
        embedder (used by mcp_server which manages its own singletons).

    Returns
    -------
    (client, embedder, cmap)  — may return an empty cmap on soft failure if the
    caller prefers not to raise (callers that need empty-dict fallback should
    catch RuntimeError).
    """
    embedder = shared_embedder or OllamaEmbeddings(model=model)
    last_exc: Optional[Exception] = None
    for attempt in range(retries):
        try:
            client = shared_client or persistent_chroma_client(db_path)
            client.list_collections()  # connectivity probe
            cmap = discover_collections(db_path, embedder, client)
            return client, embedder, cmap
        except Exception as exc:
            last_exc = exc
            log.warning("Chroma connect attempt %d failed: %s", attempt + 1, exc)
            time.sleep(delay)
    raise RuntimeError(f"ChromaDB connection failed after {retries} attempts: {last_exc}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def safe_collection_count(coll: Any) -> int:
    """Return collection.count() or 0 on any error."""
    try:
        return int(coll.count())
    except Exception:
        return 0
