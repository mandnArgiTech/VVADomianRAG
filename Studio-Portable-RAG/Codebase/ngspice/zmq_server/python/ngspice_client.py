"""ZMQ REQ client for ``ngspice-server`` (wire byte + packed ``SimRequest`` / ``SimResult``)."""

from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional, Tuple

import zmq

from ngspice_sim_pb2 import SimRequest, SimResult

WIRE_SIM = 1
WIRE_STATS = 3


class NgspiceServerError(RuntimeError):
    """Invalid reply or ngspice-server reported failure."""


class NgspiceTimeoutError(TimeoutError):
    """No ZMQ reply within ``timeout_sec``."""


def _pack_sim_request(req: SimRequest) -> bytes:
    body = req.SerializeToString()
    return bytes([WIRE_SIM]) + body


def _unpack_sim_result(data: bytes) -> SimResult:
    if len(data) < 2:
        raise NgspiceServerError("empty ZMQ reply")
    if data[0] != WIRE_SIM:
        raise NgspiceServerError("unexpected wire type %r" % (data[0],))
    out = SimResult()
    out.ParseFromString(memoryview(data)[1:])
    return out


class NgspiceClient:
    """One-shot or context-managed REQ socket to ``ngspice-server``."""

    def __init__(self, rep_url: str) -> None:
        self._url = rep_url
        self._ctx: Optional[zmq.Context] = None
        self._sock: Optional[zmq.Socket] = None

    def __enter__(self) -> NgspiceClient:
        self._ctx = zmq.Context.instance()
        self._sock = self._ctx.socket(zmq.REQ)
        self._sock.connect(self._url)
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close(linger=0)
            except Exception:
                pass
            self._sock = None
        self._ctx = None

    def simulate(
        self,
        netlist: str,
        *,
        analysis: str = "op",
        timeout_sec: float = 60.0,
        stream_diagnostics: bool = False,
        request_id: str = "",
    ) -> SimResult:
        if self._sock is None:
            raise NgspiceServerError("NgspiceClient not connected; use 'with NgspiceClient(url)'")
        req = SimRequest()
        req.netlist = netlist or ""
        req.analysis = (analysis or "op").strip().lower()
        req.stream_diagnostics = bool(stream_diagnostics)
        req.request_id = request_id or ""
        self._sock.setsockopt(zmq.RCVTIMEO, int(timeout_sec * 1000))
        try:
            self._sock.send(_pack_sim_request(req))
            data = self._sock.recv()
        except zmq.Again as e:
            raise NgspiceTimeoutError(
                "no reply from ngspice-server within %.1fs (%s)"
                % (timeout_sec, self._url)
            ) from e
        return _unpack_sim_result(data)


def simulate_transient(
    netlist: str,
    *,
    client: Optional[NgspiceClient] = None,
    timeout_sec: float = 120.0,
    request_id: str = "",
    stream_diagnostics: bool = True,
) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """
    Run ``.tran`` via ZMQ; return dict compatible with ``bridge_server._tran_cli_response``.

    Returns ``(ok, transient_dict_or_none, error_message)``.
    """
    own = client is None
    if own:
        url = os.environ.get("NGSPICE_ZMQ_REP", "tcp://127.0.0.1:5555")
        client = NgspiceClient(url)
        client.__enter__()
    assert client is not None
    try:
        res = client.simulate(
            netlist,
            analysis="tran",
            timeout_sec=timeout_sec,
            stream_diagnostics=stream_diagnostics,
            request_id=request_id,
        )
    finally:
        if own:
            client.close()
    if res.error != SimResult.OK:
        return False, None, SimResult.ErrorCode.Name(res.error)
    if not res.vectors:
        return False, None, "no vectors in SimResult"
    vecs: Dict[str, List[float]] = {}
    tvec: Optional[List[float]] = None
    for vd in res.vectors:
        name = (vd.name or "").strip()
        if not name:
            continue
        vecs[name] = list(vd.real_values)
        if name.lower() == "time":
            tvec = vecs[name]
    if tvec is None:
        return False, None, "no time vector in transient result"
    tr: Dict[str, Any] = {
        "time": tvec,
        "vectors": {k: v for k, v in vecs.items() if k.lower() != "time"},
        "actual_steps": int(res.num_points or len(tvec)),
        "rejected_steps": 0,
        "h_min_used": 0.0,
        "h_max_used": 0.0,
        "fourier": None,
        "zvs_events": [],
        "sic_desat_events": [],
        "emi_summary": None,
        "soa_events": [],
        "_wall_ms": float(res.wall_time_ms),
    }
    return True, tr, ""


async def simulate_transient_async(
    netlist: str,
    *,
    pool: "AsyncZmqSimPool",
    timeout_sec: float = 120.0,
    request_id: str = "",
    stream_diagnostics: bool = True,
) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """
    Async transient via ``AsyncZmqSimPool`` (DEALER → ROUTER).
    Returns the same tuple shape as ``simulate_transient``.
    """
    res = await pool.simulate(
        netlist,
        analysis="tran",
        timeout_sec=timeout_sec,
        stream_diagnostics=stream_diagnostics,
        request_id=request_id,
    )
    if res.error != SimResult.OK:
        return False, None, SimResult.ErrorCode.Name(res.error)
    if not res.vectors:
        return False, None, "no vectors in SimResult"
    vecs: Dict[str, List[float]] = {}
    tvec: Optional[List[float]] = None
    for vd in res.vectors:
        name = (vd.name or "").strip()
        if not name:
            continue
        vecs[name] = list(vd.real_values)
        if name.lower() == "time":
            tvec = vecs[name]
    if tvec is None:
        return False, None, "no time vector in transient result"
    tr: Dict[str, Any] = {
        "time": tvec,
        "vectors": {k: v for k, v in vecs.items() if k.lower() != "time"},
        "actual_steps": int(res.num_points or len(tvec)),
        "rejected_steps": 0,
        "h_min_used": 0.0,
        "h_max_used": 0.0,
        "fourier": None,
        "zvs_events": [],
        "sic_desat_events": [],
        "emi_summary": None,
        "soa_events": [],
        "_wall_ms": float(res.wall_time_ms),
    }
    return True, tr, ""
