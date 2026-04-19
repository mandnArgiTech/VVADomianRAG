"""
Cross-encoder reranker for post-retrieval re-scoring.

Lazy-loaded singleton: the CrossEncoder model is not loaded until the first
``rerank()`` call. Disabled by default — set ``RAG_RERANKER=1`` to enable.

Env vars
--------
RAG_RERANKER            0/1 — enable reranking (default 0)
RAG_RERANKER_MODEL      HuggingFace model (default BAAI/bge-reranker-v2-m3)
RAG_RERANKER_DEVICE     PyTorch device (default cuda:0)
RAG_RERANKER_CANDIDATES Over-fetch pool size passed from callers (default 30)
RAG_RERANKER_FP16       Use FP16 for inference (default 1)

For a minimal environment, install cross-encoder deps only via
``requirements-reranker.txt`` (see repo root); the main ``requirements.txt``
also lists ``sentence-transformers`` for full installs.
"""

from __future__ import annotations

import logging
import os
from typing import List, Optional, Tuple

logger = logging.getLogger("reranker")

_instance: Optional["Reranker"] = None


def get_reranker() -> Optional["Reranker"]:
    """Return the module-level ``Reranker`` singleton, or ``None`` if disabled.

    Checks ``RAG_RERANKER`` on every call so the flag can be toggled at runtime.
    """
    global _instance
    enabled = os.environ.get("RAG_RERANKER", "0").strip().lower()
    if enabled not in ("1", "true", "yes"):
        return None
    if _instance is None:
        _instance = Reranker(
            model_name=os.environ.get(
                "RAG_RERANKER_MODEL", "BAAI/bge-reranker-v2-m3"
            ),
            device=os.environ.get("RAG_RERANKER_DEVICE", "cuda:0"),
            use_fp16=os.environ.get("RAG_RERANKER_FP16", "1").strip().lower()
            in ("1", "true", "yes"),
        )
    return _instance


def rerank_pool_limit(k: int) -> int:
    """How many retrieval rows to keep before reranking (AC-3 over-fetch).

    When ``RAG_RERANKER`` is enabled, returns ``max(k, RAG_RERANKER_CANDIDATES)``
    so the cross-encoder sees up to ``CANDIDATES`` chunks even when the caller
    requests a small ``k``. When reranking is off, returns ``k`` (no extra work).
    """
    if os.environ.get("RAG_RERANKER", "0").strip().lower() not in ("1", "true", "yes"):
        return k
    try:
        c = int(os.environ.get("RAG_RERANKER_CANDIDATES", "30"))
    except ValueError:
        c = 30
    return max(k, max(1, c))


class Reranker:
    """Cross-encoder reranker wrapping ``sentence_transformers.CrossEncoder``.

    The underlying model is loaded lazily on the first ``rerank()`` call so
    that ``import reranker`` incurs zero startup cost when reranking is off.
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-v2-m3",
        device: str = "cuda:0",
        use_fp16: bool = True,
    ) -> None:
        self.model_name = model_name
        self.device = device
        self.use_fp16 = use_fp16
        self._model = None  # loaded lazily on first rerank()

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        try:
            from sentence_transformers import CrossEncoder  # type: ignore[import-untyped]
            import torch  # type: ignore[import-untyped]

            dev = self.device if torch.cuda.is_available() else "cpu"
            self._model = CrossEncoder(
                self.model_name,
                device=dev,
                trust_remote_code=True,
            )
            if self.use_fp16 and dev != "cpu":
                self._model.model.half()
            logger.info(
                "Reranker loaded: %s on %s (fp16=%s)",
                self.model_name,
                dev,
                self.use_fp16,
            )
        except ImportError:
            logger.warning(
                "Reranker enabled but sentence-transformers not installed. "
                "pip install sentence-transformers. Falling back to RRF/dense scoring."
            )
            self._model = None
        except Exception as exc:
            logger.warning("Failed to load reranker %s: %s", self.model_name, exc)
            self._model = None

    def rerank(
        self,
        query: str,
        documents: List[str],
        top_k: Optional[int] = None,
    ) -> List[Tuple[int, float]]:
        """Score (query, document) pairs.

        Parameters
        ----------
        query:
            The search query.
        documents:
            Candidate document texts.
        top_k:
            How many (index, score) pairs to return. ``None`` means all.

        Returns
        -------
        List of ``(original_index, score)`` sorted by score descending.
        When the model is unavailable, returns passthrough order with 0.0 scores.
        """
        self._ensure_loaded()
        n = len(documents)
        limit = top_k if top_k is not None else n
        if self._model is None or not documents:
            return [(i, 0.0) for i in range(min(limit, n))]

        pairs = [(query, doc) for doc in documents]
        scores = self._model.predict(pairs, show_progress_bar=False)

        indexed = [(i, float(s)) for i, s in enumerate(scores)]
        indexed.sort(key=lambda x: -x[1])

        if top_k is not None:
            indexed = indexed[:top_k]
        return indexed
