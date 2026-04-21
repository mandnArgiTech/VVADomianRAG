"""J5 devices: diode, diffpair, MOS from fixture .cir files."""

from __future__ import annotations

import pytest

pytest.importorskip("zmq")

from ngspice_client import NgspiceClient
from ngspice_testutil import load_cir, requires_server


@requires_server
def test_j5_02_diode_fixture_node_voltage() -> None:
    with NgspiceClient() as c:
        r = c.simulate(load_cir("diode_dc.cir"), request_id="j5-02")
    assert r.converged
    vb = dict(r.node_voltages).get("b")
    assert vb is not None and 0.4 < vb < 0.9


@requires_server
def test_diffpair_fixture_dc_converges() -> None:
    with NgspiceClient() as c:
        r = c.simulate(load_cir("diffpair.cir"), request_id="diffpair-01")
    assert r.converged
    v = dict(r.node_voltages)
    assert "n1" in v and "vcc" in v
    assert len(v) >= 2


@requires_server
def test_mosamp_fixture_dc_converges() -> None:
    with NgspiceClient() as c:
        r = c.simulate(load_cir("mosamp.cir"), request_id="mos-01")
    assert r.converged
    assert "drain" in dict(r.node_voltages)


@requires_server
def test_rc_filter_fixture_dc() -> None:
    with NgspiceClient() as c:
        r = c.simulate(load_cir("rc_filter.cir"), request_id="rc-01")
    assert r.converged
    v = dict(r.node_voltages)
    assert v.get("in") == pytest.approx(3.0)
    assert v.get("out") == pytest.approx(3.0)
