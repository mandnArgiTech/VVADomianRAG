"""Connect to Chroma + LangChain wrappers with retries."""

from __future__ import annotations

import logging
import time
from typing import Dict, Optional, Tuple

import chromadb
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings

from util.chroma_client import discover_collections, persistent_chroma_client as _persistent_chroma_client

_LOG = logging.getLogger("query")


def connect_chroma_with_retry(
    db_path: str,
    model: str,
) -> Tuple[chromadb.PersistentClient, OllamaEmbeddings, Dict[str, Chroma]]:
    last_exc: Optional[Exception] = None
    for attempt in range(3):
        try:
            client = _persistent_chroma_client(db_path)
            client.list_collections()
            embedder = OllamaEmbeddings(model=model)
            cmap = discover_collections(db_path, embedder, client)
            return client, embedder, cmap
        except Exception as exc:
            last_exc = exc
            _LOG.warning("Chroma connect attempt %d failed: %s", attempt + 1, exc)
            time.sleep(2)
    raise RuntimeError(f"ChromaDB connection failed: {last_exc}")
