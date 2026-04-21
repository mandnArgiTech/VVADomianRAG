"""J6 batch: ordering, partial failure, batch wall time vs sum."""

from __future__ import annotations

import pytest

pytest.importorskip("zmq")

from ngspice_sim_pb2 import SimRequest, SimResult

from ngspice_client import NgspiceClient
from ngspice_testutil import load_cir, requires_server


@requires_server
def test_j6_01_batch_order_matches_requests() -> None:
    div = load_cir("divider.cir")
    reqs = [
        SimRequest(netlist=div, analysis="op", request_id="b0"),
        SimRequest(netlist=div, analysis="op", request_id="b1"),
    ]
    with NgspiceClient() as c:
        out = c.simulate_batch(reqs, timeout_sec=60.0)
    assert len(out) == 2
    assert out[0].request_id == "b0"
    assert out[1].request_id == "b1"
    assert out[0].converged and out[1].converged


@requires_server
def test_j6_04_failed_circuit_does_not_abort_batch() -> None:
    good = load_cir("divider.cir")
    # Empty netlist: fast PARSE_ERROR path in server.
    bad = ""
    reqs = [
        SimRequest(netlist=good, analysis="op", request_id="ok"),
        SimRequest(netlist=bad, analysis="op", request_id="bad"),
    ]
    with NgspiceClient() as c:
        out = c.simulate_batch(reqs, timeout_sec=60.0)
    assert len(out) == 2
    assert out[0].converged
    assert out[0].request_id == "ok"
    assert out[1].request_id == "bad"
    assert out[1].error == SimResult.PARSE_ERROR


@requires_server
def test_j6_05_batch_wall_time_vs_sum_of_per_circuit() -> None:
    div = load_cir("divider.cir")
    reqs = [SimRequest(netlist=div, analysis="op", request_id=f"b{i}") for i in range(12)]
    with NgspiceClient() as c:
        tup = c.simulate_batch(reqs, timeout_sec=120.0, return_timing=True)
        assert isinstance(tup, tuple)
        results, total_ms = tup
    assert len(results) == 12
    sum_ms = sum(float(r.wall_time_ms) for r in results)
    # Parallel pool: batch wall clock should not exceed sum of per-job worker times
    # (often strictly less when pool > 1).
    assert total_ms <= sum_ms + 2.0
