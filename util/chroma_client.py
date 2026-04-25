"""Shared Chroma helpers (persistent client, embedding resolution, collection discovery)."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional

import chromadb
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings

from util.constants import DIM_TO_MODEL

_log = logging.getLogger(__name__)


def persistent_chroma_client(path: str) -> chromadb.PersistentClient:
    """Chroma client with telemetry off (faster init, production hygiene)."""
    try:
        from chromadb.config import Settings

        return chromadb.PersistentClient(
            path=path,
            settings=Settings(anonymized_telemetry=False),
        )
    except Exception:
        return chromadb.PersistentClient(path=path)


def embedding_model_from_db_path(db_path: str) -> str:
    """Resolve embedding model from on-disk DB config / Chroma dims only (no EMBEDDING_MODEL env).

    Use for ingestion paths that must match an existing VectorDB; ``detect_embedding_model`` still
    honors the env override first for query-time behavior.
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
    env_val = os.environ.get("EMBEDDING_MODEL", "").strip()
    if env_val:
        return env_val
    return embedding_model_from_db_path(db_path)


def discover_collections(
    db_path: str,
    embeddings: OllamaEmbeddings,
    chroma_client: Optional[chromadb.PersistentClient] = None,
) -> Dict[str, Chroma]:
    """Open one PersistentClient and attach LangChain Chroma stores per collection.

    Reuses ``client`` for every ``Chroma`` wrapper (avoids a second sqlite open) and uses
    ``create_collection_if_not_exists=False`` so we only bind to existing collections — the
    default ``get_or_create`` path can misbehave across Chroma / LangChain versions when a DB
    already contains data.
    """
    out: Dict[str, Chroma] = {}
    try:
        client = chroma_client or persistent_chroma_client(db_path)
        infos = client.list_collections()
    except Exception as exc:
        _log.error("discover_collections: list_collections failed for %s: %s", db_path, exc)
        return out
    if not infos:
        _log.warning(
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
            _log.error("discover_collections: failed to open collection %r: %s", name, exc)
    return out


def safe_collection_count(coll: Any) -> int:
    try:
        return int(coll.count())
    except Exception:
        try:
            return int(coll._collection.count())  # type: ignore[attr-defined]
        except Exception:
            return 0
