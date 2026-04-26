"""Python side of ``ngspice-server`` ZMQ I/O.

Wire framing: first byte is the message kind — ``WIRE_SIM`` (1) prefixes packed
``SimRequest`` / ``SimResult`` on the REP/REQ path; ``WIRE_STATS`` (3) is reserved
for the same one-byte + protobuf pattern used by stats-style probes.

- ``NgspiceClient``: synchronous **REQ** socket; ``simulate()`` sends ``WIRE_SIM``.
- ``simulate_transient_async``: async **DEALER** via ``AsyncZmqSimPool`` in
  ``ngspice_zmq_pool.py`` (bridge / high concurrency), same protobuf bodies.
- ``NgspiceDiagStream``: **SUB** to the server PUB; multipart topic (``request_id``)
  + ``DiagEvent`` payload; see ``NGSPICE_ZMQ_PUB_URL`` / ``NGSPICE_ZMQ_PUB_PORT``.

Architecture and hook semantics: ``docs/stories/STORY_J_ngspice_zmq_server.md``;
JSONL + C hooks: ``docs/stories/STORY_I_ngspice_diag_hooks.md`` (repo root paths).
"""

from __future__ import annotations

import os
import time
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

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

    def __init__(self, rep_url: Optional[str] = None) -> None:
        self._url = rep_url or os.environ.get("NGSPICE_ZMQ_REP", "tcp://127.0.0.1:5555")
        self._ctx: Optional[zmq.Context] = None
        self._sock: Optional[zmq.Socket] = None

    def __enter__(self) -> NgspiceClient:
        if self._sock is None:
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
        raise_on_error: bool = True,
    ) -> SimResult:
        own = False
        if self._sock is None:
            self.__enter__()
            own = True
        req = SimRequest()
        req.netlist = netlist or ""
        req.analysis = (analysis or "op").strip().lower()
        req.stream_diagnostics = bool(stream_diagnostics)
        req.request_id = request_id or ""
        assert self._sock is not None
        self._sock.setsockopt(zmq.RCVTIMEO, int(timeout_sec * 1000))
        try:
            self._sock.send(_pack_sim_request(req))
            data = self._sock.recv()
        except zmq.Again as e:
            raise NgspiceTimeoutError(
                "no reply from ngspice-server within %.1fs (%s)"
                % (timeout_sec, self._url)
            ) from e
        finally:
            if own:
                self.close()
        out = _unpack_sim_result(data)
        if raise_on_error and out.error != SimResult.OK:
            raise NgspiceServerError(SimResult.ErrorCode.Name(out.error))
        return out

    def simulate_batch(
        self,
        requests: Iterable[Union[SimRequest, Dict[str, Any]]],
        *,
        timeout_sec: float = 120.0,
        return_timing: bool = False,
    ) -> Union[List[SimResult], Tuple[List[SimResult], float]]:
        t0 = time.time()
        out: List[SimResult] = []
        for req in requests:
            if isinstance(req, SimRequest):
                netlist = req.netlist
                analysis = req.analysis or "op"
                rid = req.request_id
                stream_diag = bool(req.stream_diagnostics)
            else:
                netlist = str(req.get("netlist", ""))
                analysis = str(req.get("analysis", "op"))
                rid = str(req.get("request_id", ""))
                stream_diag = bool(req.get("stream_diagnostics", False))
            out.append(
                self.simulate(
                    netlist,
                    analysis=analysis,
                    timeout_sec=timeout_sec,
                    stream_diagnostics=stream_diag,
                    request_id=rid,
                    raise_on_error=False,
                )
            )
        if return_timing:
            return out, (time.time() - t0) * 1000.0
        return out


def extract_vectors(result: SimResult) -> Dict[str, List[float]]:
    out: Dict[str, List[float]] = {}
    for vd in result.vectors:
        name = (vd.name or "").strip()
        if not name:
            continue
        out[name] = list(vd.real_values)
        lower = name.lower()
        if lower.startswith("v(") and lower.endswith(")") and len(name) > 3:
            out[lower[2:-1]] = list(vd.real_values)
        if vd.imag_values:
            out[f"{name}_imag"] = list(vd.imag_values)
            if lower.startswith("v(") and lower.endswith(")") and len(name) > 3:
                out[f"{lower[2:-1]}_imag"] = list(vd.imag_values)
    return out


def compare_dc_op(
    netlist: str,
    expected: Dict[str, float],
    *,
    client: Optional[NgspiceClient] = None,
    rel_tol: float = 1e-3,
    abs_tol: float = 1e-6,
) -> Dict[str, Dict[str, Any]]:
    own = client is None
    c = client if client is not None else NgspiceClient()
    if own:
        c.__enter__()
    try:
        res = c.simulate(netlist, analysis="op", raise_on_error=False)
    finally:
        if own:
            c.close()
    got = dict(getattr(res, "node_voltages", {}) or {})
    out: Dict[str, Dict[str, Any]] = {}
    for name, exp in expected.items():
        val = got.get(name)
        if val is None:
            out[name] = {"expected": exp, "got": None, "match": False, "abs_error": None}
            continue
        err = abs(float(val) - float(exp))
        tol = max(abs_tol, rel_tol * abs(float(exp)))
        out[name] = {
            "expected": float(exp),
            "got": float(val),
            "match": err <= tol,
            "abs_error": err,
        }
    return out


def load_benchmark_manifest(path: str) -> List[str]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [str(x) for x in data if str(x).strip()]
    if isinstance(data, dict):
        if isinstance(data.get("circuits"), list):
            out: List[str] = []
            for item in data["circuits"]:
                if isinstance(item, str):
                    s = item.strip()
                    if s:
                        out.append(s)
                elif isinstance(item, dict):
                    s = str(item.get("netlist", "")).strip()
                    if s:
                        out.append(s)
            return out
        if isinstance(data.get("netlists"), list):
            return [str(x) for x in data["netlists"] if str(x).strip()]
    return []


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


# ---------------------------------------------------------------------------
# DiagEvent subscriber — Story J5 completion
# ---------------------------------------------------------------------------

from ngspice_sim_pb2 import DiagEvent  # noqa: E402


class NgspiceDiagStream:
    """
    ZMQ SUB subscriber for DiagEvent frames emitted by ngspice-server on
    the PUB socket (default tcp://localhost:5556).

    Usage::

        with NgspiceDiagStream() as stream:
            result = client.simulate(netlist, stream_diagnostics=True, request_id="r1")
            events = stream.collect(request_id="r1", timeout_sec=2.0)

    The server publishes each DiagEvent as a two-frame multipart message:
        frame 0: topic = request_id (bytes)
        frame 1: serialised DiagEvent protobuf (bytes)

    When ``request_id`` is empty or "default", the topic is b"default".
    ``collect()`` reads all available frames (non-blocking poll after
    ``timeout_sec`` drain window) and optionally filters by request_id.
    """

    DEFAULT_PUB_URL = os.environ.get(
        "NGSPICE_ZMQ_PUB_URL",
        f"tcp://localhost:{os.environ.get('NGSPICE_ZMQ_PUB_PORT', '5556')}",
    )

    def __init__(self, pub_url: Optional[str] = None) -> None:
        self._url = pub_url or self.DEFAULT_PUB_URL
        self._ctx = zmq.Context.instance()
        self._sock = self._ctx.socket(zmq.SUB)
        self._sock.setsockopt(zmq.SUBSCRIBE, b"")  # subscribe to all topics
        self._sock.setsockopt(zmq.RCVTIMEO, 0)     # non-blocking by default
        self._sock.connect(self._url)

    # ---- context manager support ----

    def __enter__(self) -> "NgspiceDiagStream":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        """Close the SUB socket."""
        try:
            self._sock.close(linger=0)
        except Exception:
            pass

    # ---- main API ----

    def collect(
        self,
        *,
        request_id: str = "",
        timeout_sec: float = 2.0,
    ) -> List["DiagEvent"]:
        """
        Drain DiagEvent frames from the PUB socket for up to ``timeout_sec``
        seconds, then return all frames matching ``request_id`` (or all frames
        if ``request_id`` is empty).

        Returns a list of decoded ``DiagEvent`` protobuf objects.
        """
        deadline = time.monotonic() + timeout_sec
        raw: List[bytes] = []

        # Blocking poll until deadline, then drain without blocking
        remaining_ms = max(1, int((deadline - time.monotonic()) * 1000))
        while time.monotonic() < deadline:
            remaining_ms = max(1, int((deadline - time.monotonic()) * 1000))
            if self._sock.poll(remaining_ms, zmq.POLLIN):
                try:
                    frames = self._sock.recv_multipart(zmq.NOBLOCK)
                    if len(frames) >= 2:
                        raw.append((frames[0], frames[1]))
                except zmq.Again:
                    pass
            else:
                break  # nothing arrived before deadline

        # Drain any remaining buffered frames non-blocking
        while True:
            try:
                frames = self._sock.recv_multipart(zmq.NOBLOCK)
                if len(frames) >= 2:
                    raw.append((frames[0], frames[1]))
            except zmq.Again:
                break

        # Decode and optionally filter
        result: List[DiagEvent] = []
        target = request_id.encode() if request_id else None
        for topic_bytes, body_bytes in raw:
            if target is not None and topic_bytes != target:
                continue
            ev = DiagEvent()
            try:
                ev.ParseFromString(body_bytes)
                result.append(ev)
            except Exception:
                pass  # malformed frame — skip

        return result
