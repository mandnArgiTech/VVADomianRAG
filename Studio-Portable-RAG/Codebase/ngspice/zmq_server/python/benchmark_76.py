#!/usr/bin/env python3
"""
Run N DC .op simulations via simulate_batch (default N=76 synthetic dividers).

Requires ngspice-server on REP 5555 and libngspice with SPICE_LIB_DIR set for the server process.

Usage:
  RUN_NGSPICE_SERVER=1 SPICE_LIB_DIR=.../install/share/ngspice \\
    Studio-Portable-RAG/Codebase/ngspice/zmq_server/ngspice-server &
  PYTHONPATH=Studio-Portable-RAG/Codebase/ngspice/zmq_server/python \\
    python3 Studio-Portable-RAG/Codebase/ngspice/zmq_server/python/benchmark_76.py

Optional manifest:
  PYTHONPATH=.../zmq_server/python python3 .../zmq_server/python/benchmark_76.py \\
    .../zmq_server/tests/fixtures/internal_dc_benchmark_manifest.json

Options:
  --rss-runs N   after benchmark, run N sequential sims and print VmRSS delta (Linux /proc).
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import List

from ngspice_client import NgspiceClient, load_benchmark_manifest


def synthetic_dividers(n: int) -> List[str]:
    """76+ varied DC dividers (different R pairs) for batch / pool stress."""
    out: List[str] = []
    for i in range(n):
        r1 = 500.0 + float(i * 17)
        r2 = 1000.0 + float(i * 13)
        out.append(
            "Bench divider deck\n"
            f"V1 in 0 5\nR1 in out {r1}\nR2 out 0 {r2}\n.op\n.end\n"
        )
    return out


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


def main() -> int:
    p = argparse.ArgumentParser(description="Batch DC benchmark against ngspice-server")
    p.add_argument(
        "manifest",
        nargs="?",
        help="JSON manifest (list or {netlists: [...]}); default: 76 synthetic circuits",
    )
    p.add_argument("--count", type=int, default=76, help="synthetic circuit count if no manifest")
    p.add_argument(
        "--rss-runs",
        type=int,
        default=0,
        help="after batch, run this many sequential sims and print VmRSS before/after (Linux)",
    )
    p.add_argument(
        "--strict-10s",
        action="store_true",
        help="exit non-zero if total wall time exceeds 10 seconds",
    )
    args = p.parse_args()

    if args.manifest:
        circuits = load_benchmark_manifest(args.manifest)
        while len(circuits) < args.count:
            circuits.extend(load_benchmark_manifest(args.manifest))
        circuits = circuits[: args.count]
    else:
        circuits = synthetic_dividers(args.count)

    client = NgspiceClient()
    try:
        t0 = time.time()
        results = client.simulate_batch(
            [{"netlist": c, "analysis": "op"} for c in circuits],
            timeout_sec=max(180.0, len(circuits) * 3.0),
            return_timing=True,
        )
        assert isinstance(results, tuple)
        res_list, total_wall_ms = results
        elapsed = time.time() - t0
    finally:
        client.close()

    passed = sum(1 for r in res_list if r.converged)
    n = len(res_list)
    avg_ms = (elapsed / n) * 1000.0 if n else 0.0
    sum_worker_ms = sum(float(r.wall_time_ms) for r in res_list)
    print(
        f"{n} circuits: {passed}/{n} converged, {elapsed:.2f}s wall, "
        f"{avg_ms:.1f}ms avg wall, batch_total_ms={total_wall_ms:.1f}, "
        f"sum_per_job_ms={sum_worker_ms:.1f}"
    )
    if args.strict_10s and elapsed > 10.0:
        print("FAIL: --strict-10s and elapsed > 10s", file=sys.stderr)
        return 2

    if args.rss_runs > 0:
        c2 = NgspiceClient()
        try:
            div = synthetic_dividers(1)[0]
            rss_before = _read_vm_rss_kb()
            for _ in range(args.rss_runs):
                r = c2.simulate(div)
                assert r.converged
            rss_after = _read_vm_rss_kb()
            print(f"RSS kb: before={rss_before} after={rss_after} (runs={args.rss_runs})")
        finally:
            c2.close()

    return 0 if passed == n else 1


if __name__ == "__main__":
    sys.exit(main())
