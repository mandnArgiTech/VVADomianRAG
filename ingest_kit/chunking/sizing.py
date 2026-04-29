"""Character/token targets for markdown and RFC chunkers."""

from __future__ import annotations

from typing import Tuple

from ingest_kit.config import DEFAULT_RFC_TOKEN_LIMIT, MODEL_TOKEN_LIMITS


def _md_char_targets(embed_model: str) -> Tuple[int, int]:
    """Derive min/max char targets for markdown domain chunks, analogous to _rfc_char_targets."""
    for key, limit in MODEL_TOKEN_LIMITS.items():
        if key in (embed_model or "").lower():
            chars_max = limit * 4
            return max(400, chars_max // 3), chars_max
    default_chars = 2048  # pragma: no cover
    return max(400, default_chars // 3), default_chars  # pragma: no cover


def _estimate_tokens(text: str) -> int:
    """Rough token count for English-ish RFC text (~4 chars/token)."""
    return max(1, len(text) // 4)


def _get_rfc_token_limit(embed_model: str) -> int:
    em = embed_model.lower()
    for key, limit in MODEL_TOKEN_LIMITS.items():
        if key in em:
            return limit
    return DEFAULT_RFC_TOKEN_LIMIT  # pragma: no cover


def _rfc_char_targets(embed_model: str) -> Tuple[int, int]:
    tok = _get_rfc_token_limit(embed_model)
    target_max = max(512, tok * 4)
    target_min = max(256, target_max // 3)
    return target_min, target_max
