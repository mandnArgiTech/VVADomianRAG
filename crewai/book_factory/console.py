"""Human-oriented console output; mirrors to the file logger when configured."""

from __future__ import annotations

import logging
import sys

from .constants import LOGGER_NAME, MAX_REASON_CHARS

_W = 64


def line(ch: str = "─") -> None:
    print(ch * _W, flush=True)


def title(text: str) -> None:
    print(f"\n┌{'─' * (_W - 2)}┐", flush=True)
    pad = max(0, _W - 4 - len(text))
    print(f"│ {text}{' ' * pad} │", flush=True)
    print(f"└{'─' * (_W - 2)}┘", flush=True)
    log = logging.getLogger(LOGGER_NAME)
    if log.handlers:
        log.info("=== %s ===", text)


def step(tag: str, text: str) -> None:
    print(f"  [{tag}] {text}", flush=True)
    log = logging.getLogger(LOGGER_NAME)
    if log.handlers:
        log.info("[%s] %s", tag, text)


def warn(text: str) -> None:
    print(f"  [warn] {text}", file=sys.stderr, flush=True)
    log = logging.getLogger(LOGGER_NAME)
    if log.handlers:
        log.warning("%s", text)


def err(text: str) -> None:
    print(f"  [err] {text}", file=sys.stderr, flush=True)
    log = logging.getLogger(LOGGER_NAME)
    if log.handlers:
        log.error("%s", text)


def clip_reason(text: str, limit: int = MAX_REASON_CHARS) -> str:
    text = text.replace("\n", " ").strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)] + "…"
