"""VidhuBijakam demo HTTP bridge (FastAPI -> ngspice ZMQ)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest
from starlette.testclient import TestClient

_ZMQ_SRV = Path(__file__).resolve().parents[1]
_TESTS = Path(__file__).resolve().parent
_VD = _ZMQ_SRV / "vidhubijakam-demo"
if str(_TESTS) not in sys.path:
    sys.path.insert(0, str(_TESTS))
if str(_VD) not in sys.path:
    sys.path.insert(0, str(_VD))

import bridge_server as br  # noqa: E402
import ngspice_tran_cli as ntc  # noqa: E402
from ngspice_client import NgspiceTimeoutError  # noqa: E402
from ngspice_sim_pb2 import SimResult  # noqa: E402
from ngspice_testutil import load_cir, requires_server  # noqa: E402


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Any:
    async def _stub_boot() -> tuple[bool, str]:
        return True, "stub-ready"

    monkeypatch.setattr(br, "refresh_zmq_boot_status", _stub_boot)
    with TestClient(br.app) as c:
        yield c


def test_parse_minimal_ngspice_binary_raw(tmp_path) -> None:
    import struct

    hdr = (
        "Title: t\nPlotname: Transient Analysis\nFlags: real\n"
        "No. Variables: 2\nNo. Points: 3\nVariables:\n"
        "0\ttime\ttime\n1\tv(a)\tvoltage\nBinary:\n"
    )
    body = struct.pack("=dddddd", 0.0, 1.0, 0.5, 2.0, 1.0, 3.0)
    p = tmp_path / "x.raw"
    p.write_bytes(hdr.encode("ascii") + body)
    t, vecs = ntc.parse_ngspice_binary_raw(p)
    assert t == [0.0, 0.5, 1.0]
    assert "v(a)" in vecs
    assert vecs["v(a)"] == [1.0, 2.0, 3.0]


def test_examples_index_and_circuit(client: TestClient) -> None:
    r = client.get("/api/examples/index")
    assert r.status_code == 200
    data = r.json()
    assert data.get("version") == 1
    assert data["categories"]
    r2 = client.get("/api/examples/circuit", params={"path": "01-basics/01-ohms-law.cir"})
    assert r2.status_code == 200
    assert ".end" in r2.json()["text"].lower()


def test_parse_netlist_models(client: TestClient) -> None:
    body = {"text": ".model ddd d()\nR1 a b 1k\n"}
    r = client.post("/api/parse-netlist", json=body)
    assert r.status_code == 200
    d = r.json()
    assert "ddd" in d.get("models", {})
    assert len(d["components"]) >= 1


def test_components_count_search_detail(client: TestClient) -> None:
    assert client.get("/api/components/count-by-type").json()["total"] == 0
    r = client.post(
        "/api/components/search",
        json={"text_query": "", "comp_type": "R", "limit": 5},
    )
    assert r.json()["results"] == []
    assert client.get("/api/components/RC0603").status_code == 404


def test_simulate_tran_uses_zmq_simulate_transient(monkeypatch: pytest.MonkeyPatch) -> None:
    """Transient analysis should use async ``simulate_transient_async`` before batch CLI."""

    async def fake_simulate_transient_async(
        netlist: str, *, pool: object = None, timeout_sec: float = 120.0, **kwargs: object
    ):
        _ = (netlist, pool, timeout_sec, kwargs)
        return (
            True,
            {
                "time": [0.0, 1e-6],
                "vectors": {"out": [0.0, 0.5]},
                "actual_steps": 2,
                "rejected_steps": 0,
                "h_min_used": 0.0,
                "h_max_used": 0.0,
                "fourier": None,
                "zvs_events": [],
                "sic_desat_events": [],
                "emi_summary": None,
                "soa_events": [],
                "_wall_ms": 2.5,
            },
            "",
        )

    async def _stub_boot() -> tuple[bool, str]:
        return True, "stub"

    monkeypatch.setattr(br, "simulate_transient_async", fake_simulate_transient_async)
    monkeypatch.setattr(br, "refresh_zmq_boot_status", _stub_boot)

    with TestClient(br.app) as client:
        r = client.post(
            "/api/simulate",
            json={
                "components": [],
                "netlist_text": "*t\nv1 n 0 1\nr1 n 0 1k\n.tran 1u 2u\n.end",
                "analysis_type": "tran",
            },
        )
    assert r.status_code == 200
    out = r.json()
    assert "diag_events" in out
    assert isinstance(out["diag_events"], list)
    assert out["solver_name"] == "ngspice-zmq-tran"
    assert out["transient"] is not None
    assert out["transient"]["time"] == [0.0, 1e-6]
    assert out["transient"]["vectors"]["out"] == [0.0, 0.5]


def test_simulate_mocked_nodalai_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakePool:
        def __init__(self, *_a: object, **_k: object) -> None:
            pass

        async def start(self) -> None:
            return None

        async def close(self) -> None:
            return None

        async def simulate(self, netlist: str, **kwargs: object) -> SimResult:
            _ = (netlist, kwargs)
            r = SimResult()
            r.error = SimResult.OK
            r.converged = True
            r.iterations = 4
            r.wall_time_ms = 1.25
            r.node_voltages["in"] = 5.0
            r.node_voltages["out"] = 2.5
            r.branch_currents["vsrc#branch"] = -0.002
            return r

        async def fetch_server_stats(self, **_kw: object):
            from ngspice_sim_pb2 import ServerStats

            return ServerStats(pool_size=1)

    async def _stub_boot() -> tuple[bool, str]:
        return True, "stub"

    monkeypatch.setattr(br, "AsyncZmqSimPool", _FakePool)
    monkeypatch.setattr(br, "refresh_zmq_boot_status", _stub_boot)

    with TestClient(br.app) as client:
        r = client.post(
            "/api/simulate",
            json={
                "components": [],
                "netlist_text": "V1 in 0 5\n...",
                "analysis_type": "op",
            },
        )
    assert r.status_code == 200
    out = r.json()
    assert "diag_events" in out
    assert isinstance(out["diag_events"], list)
    assert out["solve_time_ms"] == pytest.approx(1.25)
    assert out["dc_op"]["node_voltages"]["out"] == pytest.approx(2.5)
    assert out["nodes"]["in"]["real"] == pytest.approx(5.0)
    assert out["components"]["vsrc#branch"]["current"]["real"] == pytest.approx(-0.002)


def test_simulate_empty_netlist_422(client: TestClient) -> None:
    r = client.post("/api/simulate", json={"netlist_text": "  ", "analysis_type": "op"})
    assert r.status_code == 422


def test_boot_status_false_when_zmq_times_out(monkeypatch: pytest.MonkeyPatch) -> None:
    class _BoomPool:
        def __init__(self, *_a: object, **_k: object) -> None:
            pass

        async def start(self) -> None:
            return None

        async def close(self) -> None:
            return None

        async def simulate(self, *a: object, **k: object) -> SimResult:
            raise NgspiceTimeoutError("boom")

        async def fetch_server_stats(self, **_kw: object):
            from ngspice_sim_pb2 import ServerStats

            return ServerStats()

    monkeypatch.setattr(br, "AsyncZmqSimPool", _BoomPool)
    br.reset_boot_zmq_cache()
    with TestClient(br.app) as tc:
        b = tc.get("/api/boot/status")
    assert b.status_code == 200
    assert b.json()["ready"] is False
    assert "ZMQ" in b.json()["current_step"] or "ngspice-server" in b.json()["current_step"]


@requires_server
def test_bridge_integration_boot_and_simulate() -> None:
    """Set ``RUN_NGSPICE_SERVER=1`` with ``ngspice-server`` on ``NGSPICE_ZMQ_REP``."""
    br.reset_boot_zmq_cache()
    with TestClient(br.app) as client:
        b = client.get("/api/boot/status")
        assert b.status_code == 200
        assert b.json().get("ready") is True
        net = load_cir("divider.cir")
        s = client.post(
            "/api/simulate",
            json={"components": [], "netlist_text": net, "analysis_type": "op"},
        )
    assert s.status_code == 200, s.text
    body = s.json()
    assert body["dc_op"]["converged"] is True
    assert body["dc_op"]["node_voltages"]["out"] == pytest.approx(2.5)
