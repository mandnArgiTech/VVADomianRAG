"""Sanity checks for the built ``ngspice-server`` binary (no live ZMQ session required)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

_ZMQ_SRV = Path(__file__).resolve().parents[1]
_BINARY = _ZMQ_SRV / "ngspice-server"


@pytest.mark.skipif(not _BINARY.is_file(), reason="ngspice-server not built (run make in zmq_server)")
def test_ngspice_server_version_banner() -> None:
    r = subprocess.run(
        [str(_BINARY), "--version"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    assert "ngspice-server" in (r.stdout or "").lower() or "ngspice-server" in (r.stderr or "").lower()


@pytest.mark.skipif(not _BINARY.is_file(), reason="ngspice-server not built")
def test_ngspice_server_help_exits_zero() -> None:
    r = subprocess.run(
        [str(_BINARY), "--help"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert r.returncode == 0
    out = (r.stdout or "") + (r.stderr or "")
    assert "--request-timeout" in out or "request-timeout" in out
