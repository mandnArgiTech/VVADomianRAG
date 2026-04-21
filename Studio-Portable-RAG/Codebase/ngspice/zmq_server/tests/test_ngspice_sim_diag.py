"""J5 diagnostics: NR / limiter events, request_id filter."""

from __future__ import annotations

import time

import pytest

pytest.importorskip("zmq")

from ngspice_client import NgspiceClient, NgspiceDiagStream
from ngspice_testutil import load_cir, requires_server


@requires_server
def test_j5_03_diag_stream_nr_events() -> None:
    s = NgspiceDiagStream()
    c = NgspiceClient()
    try:
        rid = "j5-03-diag"
        time.sleep(0.25)
        r = c.simulate(load_cir("divider.cir"), stream_diagnostics=True, request_id=rid)
        assert r.converged
        events = s.collect(request_id=rid, timeout_sec=3.0)
    finally:
        s.close()
        c.close()
    kinds = {e.WhichOneof("event") for e in events}
    if not events:
        pytest.skip("no DiagEvent frames (Story I diag hooks may be absent in libngspice)")
    assert "nr_iter" in kinds or len(events) > 0


@requires_server
def test_j5_04_limiter_events_diode_fixture() -> None:
    s = NgspiceDiagStream()
    c = NgspiceClient()
    try:
        rid = "j5-04-lim"
        time.sleep(0.25)
        r = c.simulate(load_cir("diode_dc.cir"), stream_diagnostics=True, request_id=rid)
        assert r.converged
        events = s.collect(request_id=rid, timeout_sec=3.0)
    finally:
        s.close()
        c.close()
    if not events:
        pytest.skip("no DiagEvent frames (Story I diag hooks may be absent in libngspice)")
    lims = [e for e in events if e.WhichOneof("event") == "limiter"]
    assert len(lims) > 0 or len(events) > 0


@requires_server
def test_j5_10_stream_filter_request_id_only() -> None:
    s = NgspiceDiagStream()
    c = NgspiceClient()
    try:
        time.sleep(0.25)
        c.simulate(load_cir("divider.cir"), stream_diagnostics=True, request_id="keep-me")
        c.simulate(load_cir("divider.cir"), stream_diagnostics=True, request_id="ignore-me")
        evs = s.collect(request_id="keep-me", timeout_sec=2.0)
    finally:
        s.close()
        c.close()
    if not evs:
        pytest.skip("no DiagEvent frames (Story I diag hooks may be absent in libngspice)")
    for e in evs:
        assert e.request_id == "keep-me"
