"""Pytest helpers for VidhuBijakam bridge integration (optional live ngspice-server)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

_FIX = Path(__file__).resolve().parent / "fixtures"


def load_cir(name: str) -> str:
    p = _FIX / name
    if not p.is_file():
        raise FileNotFoundError(p)
    return p.read_text(encoding="utf-8", errors="replace")


def requires_server(fn):
    """Skip unless ``RUN_NGSPICE_SERVER=1`` (live ZMQ server)."""
    return pytest.mark.skipif(
        os.environ.get("RUN_NGSPICE_SERVER", "").strip() != "1",
        reason="set RUN_NGSPICE_SERVER=1 to run live ngspice-server tests",
    )(fn)
