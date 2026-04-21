"""J5 basic: divider from fixture file, parse error, context manager."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

pytest.importorskip("zmq")

from ngspice_sim_pb2 import SimResult

from ngspice_client import NgspiceClient, compare_dc_op
from ngspice_testutil import load_cir, requires_server


@requires_server
def test_j5_01_divider_from_fixture_file() -> None:
    net = load_cir("divider.cir")
    with NgspiceClient() as c:
        r = c.simulate(net, request_id="j5-01-fix")
    assert r.converged
    assert dict(r.node_voltages)["in"] == pytest.approx(5.0)
    assert dict(r.node_voltages)["out"] == pytest.approx(2.5)


@requires_server
def test_j5_07_parse_error_returned() -> None:
    with NgspiceClient() as c:
        # Empty netlist is rejected immediately (avoids ngspice hangs on some junk decks).
        r = c.simulate("", raise_on_error=False)
    assert r.error == SimResult.PARSE_ERROR


@requires_server
def test_j5_08_context_manager_closes() -> None:
    c = NgspiceClient()
    with c:
        c.simulate(load_cir("divider.cir"))
    assert c._sock is None


def test_compare_dc_op_unit_only() -> None:
    """No server: diff structure still builds."""
    mock_res = MagicMock(spec=SimResult)
    mock_res.error = SimResult.OK
    mock_res.node_voltages = {"n": 1.0}
    c = MagicMock()
    c.simulate.return_value = mock_res
    d = compare_dc_op("x", {"n": 1.0}, client=c)
    assert d["n"]["match"]


@requires_server
def test_j5_05_compare_dc_op_match_fixture() -> None:
    d = compare_dc_op(load_cir("divider.cir"), {"in": 5.0, "out": 2.5})
    assert d["in"]["match"] and d["out"]["match"]
