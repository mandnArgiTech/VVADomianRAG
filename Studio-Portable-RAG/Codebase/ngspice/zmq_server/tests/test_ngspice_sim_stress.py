"""J5/J6 stress: many sequential sims, RSS drift, 76-circuit batch."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

pytest.importorskip("zmq")

from ngspice_client import NgspiceClient, load_benchmark_manifest
from ngspice_testutil import load_cir, requires_server


def _read_vm_rss_kb() -> int:
    try:
        txt = Path("/proc/self/status").read_text(encoding="utf-8")
    except OSError:
        return 0
    for line in txt.splitlines():
        if line.startswith("VmRSS:"):
            parts = line.split()
            return int(parts[1]) if len(parts) >= 2 else 0
    return 0


@requires_server
def test_j5_09_hundred_sequential_sims() -> None:
    div = load_cir("divider.cir")
    with NgspiceClient() as c:
        for i in range(100):
            r = c.simulate(div, request_id=f"seq-{i}")
            assert r.converged, f"iteration {i}"


@requires_server
def test_j6_02_rss_stable_across_sequential_requests() -> None:
    div = load_cir("divider.cir")
    rss0 = _read_vm_rss_kb()
    with NgspiceClient() as c:
        for _ in range(50):
            r = c.simulate(div)
            assert r.converged
    rss1 = _read_vm_rss_kb()
    if rss0 > 0 and rss1 > 0:
        # Allow growth (Python client + libc); catch runaway leaks only
        assert rss1 < rss0 * 4 + 200_000


@requires_server
def test_j6_03_seventy_six_circuit_batch_under_budget() -> None:
    manifest = (
        Path(__file__).resolve().parent / "fixtures" / "internal_dc_benchmark_manifest.json"
    )
    if manifest.exists():
        circuits = load_benchmark_manifest(str(manifest))
        while len(circuits) < 76:
            circuits.extend(load_benchmark_manifest(str(manifest)))
        circuits = circuits[:76]
    else:
        circuits = [
            f"Title line\nV1 in 0 5\nR1 in out {1000+i}\nR2 out 0 {1000+i}\n.op\n.end\n"
            for i in range(76)
        ]
    with NgspiceClient() as c:
        t0 = time.time()
        results = c.simulate_batch(
            [{"netlist": n, "analysis": "op"} for n in circuits],
            timeout_sec=max(180.0, len(circuits) * 3.0),
        )
        elapsed = time.time() - t0
    passed = sum(1 for r in results if r.converged)
    assert passed == len(circuits)
    strict = os.environ.get("STRICT_NGSPICE_BENCH", "").lower() in ("1", "true", "yes")
    limit = 10.0 if strict else 45.0
    assert elapsed < limit, f"batch took {elapsed:.1f}s (limit {limit}s)"


@requires_server
def test_j6_06_benchmark_manifest_loads() -> None:
    p = Path(__file__).resolve().parent / "fixtures" / "internal_dc_benchmark_manifest.json"
    if not p.exists():
        pytest.skip("manifest missing")
    nets = load_benchmark_manifest(str(p))
    assert len(nets) >= 1
