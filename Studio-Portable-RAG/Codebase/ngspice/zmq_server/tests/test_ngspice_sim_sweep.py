"""Integration: .tran, .ac, .dc via ZMQ server (RUN_NGSPICE_SERVER=1)."""

from __future__ import annotations

import math

import pytest

pytest.importorskip("zmq")

from ngspice_sim_pb2 import SimResult

from ngspice_client import NgspiceClient, extract_vectors, simulate_transient
from ngspice_testutil import load_cir, requires_server


@requires_server
def test_tran_rc_charging() -> None:
    net = load_cir("rc_tran.cir")
    with NgspiceClient() as c:
        r = c.simulate(net, analysis="tran", request_id="sweep-tran")
    assert r.error == SimResult.OK
    assert r.converged
    assert r.analysis_type.lower() == "tran"
    assert r.num_points > 10
    vecs = extract_vectors(r)
    assert "time" in vecs
    vout = vecs.get("out") or vecs.get("v(out)")
    assert vout is not None and len(vout) == r.num_points
    assert vout[-1] > vout[0] + 0.02
    assert vout[-1] < 1.0  # partial charge toward steady state (1V)


@requires_server
def test_tran_num_points() -> None:
    net = load_cir("rc_tran.cir")
    with NgspiceClient() as c:
        r = c.simulate(net, analysis="tran")
    assert r.num_points > 0


@requires_server
def test_ac_rc_lowpass() -> None:
    net = load_cir("rc_ac.cir")
    with NgspiceClient() as c:
        r = c.simulate(net, analysis="ac", request_id="sweep-ac")
    assert r.error == SimResult.OK
    assert r.converged
    assert r.analysis_type.lower() == "ac"
    vecs = extract_vectors(r)
    freq = vecs.get("frequency") or vecs.get("hertz")
    assert freq is not None and len(freq) >= 2
    vout_r = vecs.get("out") or vecs.get("v(out)")
    vout_i = vecs.get("out_imag")
    assert vout_r is not None

    def mag(i: int) -> float:
        re = vout_r[i]
        im = vout_i[i] if vout_i and i < len(vout_i) else 0.0
        return math.hypot(re, im)

    mag_lo = mag(0)
    mag_hi = mag(len(vout_r) - 1)
    assert mag_hi < mag_lo * 0.5


@requires_server
def test_ac_complex_values() -> None:
    net = load_cir("rc_ac.cir")
    with NgspiceClient() as c:
        r = c.simulate(net, analysis="ac")
    assert r.vectors
    out_v = next(
        (v for v in r.vectors if v.name and v.name.lower() == "out"),
        None,
    )
    assert out_v is not None
    assert len(out_v.imag_values) > 0


@requires_server
def test_dc_sweep_divider() -> None:
    net = load_cir("divider_dc.cir")
    with NgspiceClient() as c:
        r = c.simulate(net, analysis="dc", request_id="sweep-dc")
    assert r.error == SimResult.OK
    assert r.converged
    vecs = extract_vectors(r)
    vout = vecs.get("out") or vecs.get("v(out)")
    assert vout is not None
    sweep = vecs.get("v-sweep") or vecs.get("v(v1)") or vecs.get("v1")
    assert sweep is not None and len(sweep) == len(vout)
    for i, sv in enumerate(sweep):
        if abs(sv) < 1e-9:
            continue
        assert vout[i] / sv == pytest.approx(0.5, rel=0.02)


@requires_server
def test_op_still_works_and_analysis_type() -> None:
    net = load_cir("divider.cir")
    with NgspiceClient() as c:
        r = c.simulate(net, analysis="op")
    assert r.converged
    assert (r.analysis_type or "").lower() == "op"
    assert dict(r.node_voltages)["out"] == pytest.approx(2.5)


@requires_server
def test_unknown_analysis_falls_back_to_op() -> None:
    net = load_cir("divider.cir")
    with NgspiceClient() as c:
        r = c.simulate(net, analysis="nosuch", raise_on_error=False)
    assert r.converged
    assert (r.analysis_type or "").lower() == "op"
    w = " ".join(r.warnings).lower()
    assert "unknown" in w


@requires_server
def test_simulate_transient_helper() -> None:
    net = load_cir("rc_tran.cir")
    ok, payload, msg = simulate_transient(net)
    assert ok and msg == ""
    assert payload is not None
    assert len(payload["time"]) >= 2
    assert "vectors" in payload
    assert payload["actual_steps"] > 0
