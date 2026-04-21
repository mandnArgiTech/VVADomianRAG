"""Thin client checks; full integration tests live under ``zmq_server/tests/test_ngspice_sim_*.py``.

Run: ``pytest Studio-Portable-RAG/Codebase/ngspice/zmq_server/tests/test_ngspice_sim_basic.py -o addopts=``
  (with ``RUN_NGSPICE_SERVER=1``).
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("zmq")
from ngspice_sim_pb2 import SimRequest, SimResult

from ngspice_client import NgspiceClient, NgspiceDiagStream, compare_dc_op


def _integration_enabled() -> bool:
    return os.environ.get("RUN_NGSPICE_SERVER", "").lower() in ("1", "true", "yes")


requires_server = pytest.mark.skipif(
    not _integration_enabled(),
    reason="set RUN_NGSPICE_SERVER=1 with ngspice-server on 5555/5556",
)


DIVIDER = """V1 in 0 5
R1 in out 1k
R2 out 0 1k
.op
.end
"""


@requires_server
def test_simulate_divider_voltages() -> None:
    with NgspiceClient() as c:
        r = c.simulate(DIVIDER, request_id="j5-01")
    assert r.converged
    assert dict(r.node_voltages)["in"] == pytest.approx(5.0)
    assert dict(r.node_voltages)["out"] == pytest.approx(2.5)


@requires_server
def test_simulate_diode_branch() -> None:
    net = """V1 a 0 5
R1 a b 1k
D1 b 0 DMOD
.model DMOD D(IS=2.52e-9 N=1.752)
.op
.end
"""
    with NgspiceClient() as c:
        r = c.simulate(net, request_id="j5-02")
    assert r.converged
    vb = dict(r.node_voltages).get("b")
    assert vb is not None and 0.4 < vb < 0.9


@requires_server
def test_diag_stream_nr_events() -> None:
    import time as _time

    s = NgspiceDiagStream()
    c = NgspiceClient()
    try:
        rid = "j5-03"
        _time.sleep(0.05)
        r = c.simulate(DIVIDER, stream_diagnostics=True, request_id=rid)
        assert r.converged
        events = s.collect(request_id=rid, timeout_sec=2.0)
    finally:
        s.close()
        c.close()
    kinds = {e.WhichOneof("event") for e in events}
    assert "nr_iter" in kinds or len(events) > 0


@requires_server
def test_compare_dc_op_match() -> None:
    d = compare_dc_op(DIVIDER, {"in": 5.0, "out": 2.5})
    assert d["in"]["match"] and d["out"]["match"]


@requires_server
def test_parse_error_returned() -> None:
    with NgspiceClient() as c:
        r = c.simulate("not a spice deck\n.end\n", raise_on_error=False)
    assert r.error == SimResult.PARSE_ERROR


@requires_server
def test_context_manager_closes() -> None:
    c = NgspiceClient()
    with c:
        c.simulate(DIVIDER)
    assert c._sock is None


@requires_server
def test_batch_order() -> None:
    reqs = [
        SimRequest(netlist=DIVIDER, analysis="op", request_id="b0"),
        SimRequest(netlist=DIVIDER, analysis="op", request_id="b1"),
    ]
    with NgspiceClient() as c:
        out = c.simulate_batch(reqs, timeout_sec=30.0)
    assert len(out) == 2
    assert out[0].request_id == "b0"
    assert out[1].request_id == "b1"
    assert out[0].converged and out[1].converged


def test_compare_dc_op_unit_only() -> None:
    """No server: logic still builds diff structure."""
    from unittest.mock import MagicMock

    mock_res = MagicMock(spec=SimResult)
    mock_res.error = SimResult.OK
    mock_res.node_voltages = {"n": 1.0}
    c = MagicMock()
    c.simulate.return_value = mock_res
    d = compare_dc_op("x", {"n": 1.0}, client=c)
    assert d["n"]["match"]
