"""Ollama availability checks, model resolution, and chat ``options`` helpers."""

from __future__ import annotations

import json
import logging
import os
import urllib.request
from typing import Any, Dict, List

from query_kit.config import CHAT_MODEL_FALLBACKS, DEFAULT_CHAT_LLM

try:
    import ollama as _ollama_mod

    OLLAMA_LIB_AVAILABLE = True
except ImportError:  # pragma: no cover
    _ollama_mod = None  # type: ignore[assignment]
    OLLAMA_LIB_AVAILABLE = False


_LOG = logging.getLogger("query")


def estimate_tokens(text: str, provider: str = "ollama") -> int:
    """Rough token count without a tokenizer: Claude ~4 chars/token, others ~3.5."""
    if not text:
        return 0
    divisor = 4.0 if provider == "anthropic" else 3.5
    return max(1, int(len(text) / divisor))


def check_ollama(timeout: float = 3.0) -> bool:
    try:
        urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=timeout)
        return True
    except Exception:
        return False


def default_chat_llm_from_env() -> str:
    env = (os.environ.get("RAG_LLM_MODEL", "") or "").strip()
    return env or DEFAULT_CHAT_LLM


def ollama_base_url() -> str:
    return (os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")).rstrip("/")


def tag_matches_model(tag: str, want: str) -> bool:
    if not want or not tag:
        return False
    if tag == want or tag.startswith(want + ":"):
        return True
    if ":" not in want:
        return tag.split(":")[0] == want.split(":")[0]
    return False


def pick_ollama_model_tag(names: List[str], want: str) -> str:
    for n in names:
        if n and tag_matches_model(n, want):
            return n
    return ""


def ollama_chat_model_names() -> List[str]:
    url = ollama_base_url() + "/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read().decode())
    except Exception:
        return []
    models = data.get("models") or []
    return [str(m.get("name") or "") for m in models if m.get("name")]


def check_model_available(model: str) -> str:
    """Return an Ollama tag that matches ``model`` if present; else first matching fallback tag."""
    names = ollama_chat_model_names()
    want = (model or "").strip() or default_chat_llm_from_env()
    if not names:
        return want
    tag = pick_ollama_model_tag(names, want)
    if tag:
        return tag
    _LOG.warning(
        "Default model %s not found. Run: ollama pull %s",
        want,
        want.split(":")[0] if want else want,
    )
    for fb in CHAT_MODEL_FALLBACKS:
        tag = pick_ollama_model_tag(names, fb)
        if tag:
            _LOG.info("Falling back to Ollama model: %s", tag)
            return tag
    _LOG.warning("No fallback model found in Ollama tags. Using %s anyway.", want)
    return want


def ollama_options_for_model(model_name: str) -> Dict[str, Any]:
    """Ollama ``options`` for chat; Gemma gets larger context and repeat_penalty."""
    tag = (model_name or "").lower()
    if "gemma" in tag:
        return {
            "num_ctx": 65536,
            "temperature": 0.1,
            "top_p": 0.9,
            "repeat_penalty": 1.1,
        }
    return {
        "num_ctx": 32768,
        "temperature": 0.2,
        "top_p": 0.95,
    }


def stream_chunk_text(chunk: Any) -> str:
    if chunk is None:
        return ""
    msg = getattr(chunk, "message", None)
    if msg is None and isinstance(chunk, dict):
        msg = chunk.get("message")
    if msg is None:
        return ""
    if isinstance(msg, dict):
        return str(msg.get("content") or "")
    return str(getattr(msg, "content", None) or "")


# Shim aliases (historical ``query._`` names)
_check_model_available = check_model_available
_ollama_options_for_model = ollama_options_for_model
_stream_chunk_text = stream_chunk_text
_ollama_base_url = ollama_base_url
_tag_matches_model = tag_matches_model
_pick_ollama_model_tag = pick_ollama_model_tag
