"""
HTTP API shim for the VidhuBijakam kernel demo UI: translates NodalAI-style /api/*
calls to ngspice-server over ZMQ (NgspiceClient).

**Recommended:** from ``zmq_server/`` run ``./ng.sh up`` — reads ``ng.yaml`` and starts
``ngspice-server``, this bridge, and Vite without hand-maintained shell exports.

Manual run (from this directory, after ``pip install -r requirements-bridge.txt``)::

  export PYTHONPATH=../python
  uvicorn bridge_server:app --host 127.0.0.1 --port 8000

Requires ``ngspice-server`` on ``NGSPICE_ZMQ_REP`` (default ``tcp://127.0.0.1:5555``; ZMQ ROUTER, REQ clients compatible).
When started by ``ng.sh``, ``NGSPICE_ZMQ_REP`` is set from ``ng.yaml`` for this process only.

Environment (optional overrides when not using ``ng.sh``):

- ``NGSPICE_ZMQ_REP`` — ZMQ ROUTER URL for ``ngspice-server``.
- ``NGSPICE_ZMQ_PUB`` — ZMQ PUB URL for diagnostic ``DiagEvent`` stream (default ``tcp://127.0.0.1:5556``).
- ``NGSPICE_ZMQ_POOL`` — DEALER pool size for the async bridge (default ``8``).
- ``NGSPICE_BOOT_CACHE_SEC`` — TTL for the cached ZMQ reachability ping used by
  ``GET /api/boot/status`` (default ``5``).
- ``NGSPICE_PROMETHEUS`` — If not ``0``, expose ``GET /metrics`` when ``prometheus_client`` is installed.
- ``NGSPICE_CLI`` — Optional path to the **batch** ``ngspice`` executable used only as a
  **fallback** for ``.tran`` when the ZMQ transient run fails. ``PATH`` is searched if unset.
  The primary path for ``.tran`` / ``.ac`` / ``.dc`` / ``.op`` is ``ngspice-server`` over ZMQ.
"""

from __future__ import annotations

import asyncio
import os
import re
import sys
import threading
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

import zmq
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response
from google.protobuf.json_format import MessageToDict
from pydantic import BaseModel, Field

_THIS = Path(__file__).resolve().parent
_EXAMPLES = (_THIS / "examples").resolve()
_PY_CLIENT = (_THIS.parent / "python").resolve()

if str(_PY_CLIENT) not in sys.path:
    sys.path.insert(0, str(_PY_CLIENT))
if str(_THIS) not in sys.path:
    sys.path.insert(0, str(_THIS))

from ngspice_client import (  # noqa: E402
    NgspiceClient,
    NgspiceServerError,
    NgspiceTimeoutError,
    simulate_transient,
    simulate_transient_async,
)
from ngspice_sim_pb2 import DiagEvent, SimResult  # noqa: E402
from ngspice_zmq_pool import AsyncZmqSimPool  # noqa: E402

from ngspice_tran_cli import run_transient  # noqa: E402

try:
    from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

    _PROM_LIB = True
    _SIM_TOTAL = Counter(
        "ngspice_bridge_simulate_total",
        "POST /api/simulate terminal outcomes",
        ("result",),
    )
except ImportError:
    _PROM_LIB = False
    _SIM_TOTAL = None  # type: ignore[assignment]


def _prometheus_enabled() -> bool:
    return bool(
        _PROM_LIB
        and os.environ.get("NGSPICE_PROMETHEUS", "1").strip().lower() not in ("0", "false", "no")
    )


def _sim_metric(result: str) -> None:
    if _SIM_TOTAL is not None:
        _SIM_TOTAL.labels(result).inc()


# libngspice vector names for node voltages are often plain identifiers (``out``), not ``v(out)``.
_VTRAN_NODE_VECTOR = re.compile(r"^[a-z][a-z0-9_]*$")


def _cv(x: float) -> dict:
    return {"real": float(x), "imag": 0.0, "mag": abs(float(x)), "phase_deg": 0.0}


def _cr(i: float, v: float = 0.0) -> dict:
    return {"voltage": _cv(v), "current": _cv(i), "power": _cv(0.0)}


def _nodes_from_tran_vectors(vectors: dict[str, list[float]]) -> dict[str, dict]:
    nodes: dict[str, dict] = {}
    for k, arr in vectors.items():
        if not arr:
            continue
        lk = k.lower()
        if lk.startswith("v(") and lk.endswith(")"):
            nodes[lk[2:-1]] = _cv(float(arr[-1]))
        elif (
            lk not in ("time",)
            and not lk.endswith("_imag")
            and _VTRAN_NODE_VECTOR.fullmatch(lk)
        ):
            nodes[lk] = _cv(float(arr[-1]))
    return nodes


def _dc_op_from_tran_last(vectors: dict[str, list[float]]) -> dict:
    nv: dict[str, float] = {}
    bc: dict[str, float] = {}
    for k, arr in vectors.items():
        if not arr:
            continue
        lk = k.lower()
        if lk.startswith("v(") and lk.endswith(")"):
            nv[lk[2:-1]] = float(arr[-1])
        elif lk not in ("time",) and not lk.endswith("_imag") and _VTRAN_NODE_VECTOR.fullmatch(lk):
            nv[lk] = float(arr[-1])
        elif lk.startswith("i(") and lk.endswith(")"):
            bc[lk[2:-1] + "#branch"] = float(arr[-1])
    return {
        "node_voltages": nv,
        "branch_currents": bc,
        "converged": True,
        "iterations": 0,
        "convergence_hints": [],
    }


def _components_from_tran_last(vectors: dict[str, list[float]]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for k, arr in vectors.items():
        if not arr:
            continue
        lk = k.lower()
        if lk.startswith("i(") and lk.endswith(")"):
            out[lk[2:-1] + "#branch"] = _cr(float(arr[-1]))
    return out


def _tran_cli_response(
    tr: dict, *, wall_ms: float, analysis_type: str, solver_name: str = "ngspice-cli-tran"
) -> dict:
    """Build NodalAI-shaped JSON after a successful transient (ZMQ or ``ngspice -b``)."""
    vecs = {k: list(v) for k, v in tr["vectors"].items()}
    t = list(tr["time"])
    tr_block = {
        "time": t,
        "vectors": vecs,
        "actual_steps": int(tr.get("actual_steps", len(t))),
        "rejected_steps": int(tr.get("rejected_steps", 0)),
        "h_min_used": float(tr.get("h_min_used", 0.0)),
        "h_max_used": float(tr.get("h_max_used", 0.0)),
        "fourier": tr.get("fourier"),
        "zvs_events": tr.get("zvs_events") or [],
        "sic_desat_events": tr.get("sic_desat_events") or [],
        "emi_summary": tr.get("emi_summary"),
        "soa_events": tr.get("soa_events") or [],
    }
    return {
        "nodes": _nodes_from_tran_vectors(vecs),
        "components": _components_from_tran_last(vecs),
        "drc_message": "",
        "analysis_type": analysis_type,
        "expansion_log": [],
        "expansion_errors": [],
        "transient": tr_block,
        "ac_sweep": None,
        "pole_zero": None,
        "noise": None,
        "dc_op": _dc_op_from_tran_last(vecs),
        "dc_sweep": None,
        "warnings": [],
        "solver_stderr": [],
        "solve_time_ms": float(wall_ms),
        "solver_name": solver_name,
        "nr_iterations": 0,
        "lte_steps": len(t),
        "c_accel_loaded": False,
        "diag_events": [],
    }


def _sim_to_simulation_response(
    res: SimResult,
    *,
    analysis_type: str,
) -> dict:
    nv = dict(res.node_voltages)
    bc = dict(res.branch_currents)
    nodes = {k: _cv(v) for k, v in nv.items()}
    components = {k: _cr(i) for k, i in bc.items()}
    err_name = (
        SimResult.ErrorCode.Name(res.error) if res.error != SimResult.OK else ""
    )
    warnings = list(res.warnings)
    if err_name:
        warnings = [f"ngspice-server: {err_name}"] + warnings
    dc_op = {
        "node_voltages": nv,
        "branch_currents": bc,
        "converged": bool(res.converged) and res.error == SimResult.OK,
        "iterations": int(res.iterations),
        "convergence_hints": [],
    }
    return {
        "nodes": nodes,
        "components": components,
        "drc_message": "",
        "analysis_type": analysis_type,
        "expansion_log": [],
        "expansion_errors": [],
        "transient": None,
        "ac_sweep": None,
        "pole_zero": None,
        "noise": None,
        "dc_op": dc_op,
        "dc_sweep": None,
        "warnings": warnings,
        "solver_stderr": [] if res.error == SimResult.OK else [err_name or "error"],
        "solve_time_ms": float(res.wall_time_ms),
        "solver_name": "ngspice-zmq",
        "nr_iterations": int(res.iterations),
        "lte_steps": 0,
        "c_accel_loaded": False,
        "diag_events": [],
    }


def _safe_example_path(rel: str) -> Path:
    p = Path(rel.strip())
    if p.is_absolute() or ".." in p.parts:
        raise HTTPException(status_code=400, detail="invalid path")
    full = (_EXAMPLES / p).resolve()
    try:
        full.relative_to(_EXAMPLES)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="path outside examples") from e
    return full


class SimulateBody(BaseModel):
    components: list = Field(default_factory=list)
    netlist_text: str = ""
    analysis_type: str = "op"


class ParseBody(BaseModel):
    text: str = ""


class AIRequest(BaseModel):
    api_key: str = ""
    prompt: str = ""
    provider: str = ""


class ComponentSearchBody(BaseModel):
    text_query: str = ""
    comp_type: str = ""
    limit: int = 20


def get_rep_url() -> str:
    """ZMQ REP endpoint for ``ngspice-server`` (override with ``NGSPICE_ZMQ_REP``)."""
    return os.environ.get("NGSPICE_ZMQ_REP", "tcp://127.0.0.1:5555")


def get_pub_url() -> str:
    """ZMQ PUB endpoint for ``DiagEvent`` stream (override with ``NGSPICE_ZMQ_PUB``)."""
    return os.environ.get("NGSPICE_ZMQ_PUB", "tcp://127.0.0.1:5556")


def _diag_event_to_dict(ev: DiagEvent) -> dict:
    base: dict = {"ts_us": int(ev.timestamp_us)}
    which = ev.WhichOneof("event")
    if which == "nr_iter" and ev.nr_iter is not None:
        f = ev.nr_iter
        return {
            **base,
            "hook": "nr_iter",
            "iter": int(f.iter),
            "max_dx": float(f.max_dx),
            "max_rhs": float(f.max_rhs),
            "damp": float(f.damp),
            "noncon": int(f.noncon),
            "converged": bool(f.converged),
        }
    if which == "limiter" and ev.limiter is not None:
        f = ev.limiter
        return {
            **base,
            "hook": "limiter",
            "fn": f.function or "",
            "inst": f.instance or "",
            "vnew_raw": float(f.vnew_raw),
            "vnew_lim": float(f.vnew_limited),
            "vold": float(f.vold),
            "vcrit": float(f.vcrit),
            "vto": float(f.vto),
        }
    if which == "gmin" and ev.gmin is not None:
        f = ev.gmin
        return {
            **base,
            "hook": "gmin",
            "val": float(f.value),
            "converged": bool(f.converged),
            "iters": int(f.iterations),
        }
    if which == "src_step" and ev.src_step is not None:
        f = ev.src_step
        return {
            **base,
            "hook": "src_step",
            "factor": float(f.factor),
            "converged": bool(f.converged),
            "iters": int(f.iterations),
        }
    if which == "device" and ev.device is not None:
        f = ev.device
        vals = {e.key: float(e.value) for e in f.values}
        return {
            **base,
            "hook": "device",
            "type": f.type or "",
            "inst": f.instance or "",
            "values": vals,
        }
    if which == "matrix" and ev.matrix is not None:
        f = ev.matrix
        return {
            **base,
            "hook": "matrix",
            "size": int(f.size),
            "min_piv": float(f.min_pivot),
            "max_piv": float(f.max_pivot),
            "ratio": float(f.condition_ratio),
        }
    return {**base, "hook": "unknown", "which": which or ""}


class DiagCollector(threading.Thread):
    """SUB socket: collect packed ``DiagEvent`` frames until ``stop()``."""

    def __init__(self, pub_url: str, request_id: str, max_events: int = 2000) -> None:
        super().__init__(daemon=True)
        self._url = pub_url
        self._req_id = request_id or ""
        self._max = max_events
        self._halt = threading.Event()
        self.events: list[dict] = []

    def run(self) -> None:
        ctx = zmq.Context.instance()
        sub = ctx.socket(zmq.SUB)
        topic = (self._req_id or "default").encode("utf-8")
        try:
            sub.setsockopt(zmq.RCVTIMEO, 50)
            sub.setsockopt(zmq.SUBSCRIBE, topic)
            sub.connect(self._url)
        except Exception:
            try:
                sub.close(linger=0)
            except Exception:
                pass
            return
        while not self._halt.is_set():
            if len(self.events) >= self._max:
                break
            try:
                parts = sub.recv_multipart()
            except zmq.Again:
                continue
            except Exception:
                break
            raw = b""
            if len(parts) >= 2:
                raw = parts[-1]
            elif parts:
                raw = parts[0]
            try:
                ev = DiagEvent()
                ev.ParseFromString(bytes(raw))
            except Exception:
                continue
            rid = ev.request_id or ""
            if self._req_id and rid and rid != self._req_id:
                continue
            self.events.append(_diag_event_to_dict(ev))
        try:
            sub.close(linger=0)
        except Exception:
            pass

    def stop(self) -> None:
        self._halt.set()


_BOOT_LOCK = threading.Lock()
_boot_zmq_cache: dict[str, object] = {
    "ts": 0.0,
    "ok": False,
    "msg": "unchecked",
}
BOOT_ZMQ_CACHE_TTL_SEC = float(os.environ.get("NGSPICE_BOOT_CACHE_SEC", "5"))
_PING_NETLIST = """* ngspice-server reachability ping (nodes must be alphanumeric/underscore; no leading _)
v1 n1 0 dc 1
r1 n1 0 1k
.end
"""


def reset_boot_zmq_cache() -> None:
    """Clear cached ZMQ ping (for tests or after ``ngspice-server`` restart)."""
    with _BOOT_LOCK:
        _boot_zmq_cache["ts"] = 0.0
        _boot_zmq_cache["ok"] = False
        _boot_zmq_cache["msg"] = "unchecked"


def _boot_failure_hint(exc: BaseException, rep: str) -> str:
    """Human-readable ``current_step`` when ``ready`` is false (shown in UI tooltip / badge)."""
    name = type(exc).__name__
    low = str(exc).lower()
    if isinstance(exc, NgspiceTimeoutError) or "timeout" in low or "again" in low:
        return (
            f"No ZMQ reply from ngspice-server ({rep}). "
            "In another terminal: cd …/zmq_server && export SPICE_LIB_DIR=…/install/share/ngspice && ./ngspice-server"
        )
    if "refused" in low or "econnrefused" in low or name == "ConnectionRefusedError":
        return (
            f"Cannot reach {rep} (connection refused). Start ./ngspice-server on that ROUTER port, "
            "or set NGSPICE_ZMQ_REP to match your server."
        )
    return f"{name}: {exc}"[:220]


async def refresh_zmq_boot_status() -> tuple[bool, str]:
    """Run a tiny OP once per ``BOOT_ZMQ_CACHE_TTL_SEC``; drives ``/api/boot/status`` ``ready`` flag."""
    now = time.monotonic()
    with _BOOT_LOCK:
        ts = float(_boot_zmq_cache["ts"])
        if now - ts < BOOT_ZMQ_CACHE_TTL_SEC and ts > 0:
            return bool(_boot_zmq_cache["ok"]), str(_boot_zmq_cache["msg"])
    ok = False
    msg = ""
    rep = get_rep_url()
    try:
        pool: AsyncZmqSimPool | None = getattr(app.state, "zmq_pool", None)
        if pool is not None:
            r = await pool.simulate(_PING_NETLIST, timeout_sec=3.0)
        else:

            def _ping() -> SimResult:
                with NgspiceClient(rep) as client:
                    return client.simulate(_PING_NETLIST, timeout_sec=3.0)

            r = await asyncio.to_thread(_ping)
        ok = r.error == SimResult.OK and len(r.node_voltages) >= 1
        if ok:
            msg = "ngspice-server OK"
        elif r.error == SimResult.OK:
            msg = (
                "ngspice replied OK but returned no node voltages (unexpected). "
                f"Check SPICE_LIB_DIR / ngspice install. ZMQ: {rep}"
            )
        else:
            msg = f"ngspice-server error: {SimResult.ErrorCode.Name(r.error)} (ZMQ {rep})"
    except (NgspiceTimeoutError, NgspiceServerError, OSError) as e:
        ok = False
        msg = _boot_failure_hint(e, rep)
    except Exception as e:  # pragma: no cover - defensive
        ok = False
        msg = _boot_failure_hint(e, rep)
    with _BOOT_LOCK:
        _boot_zmq_cache["ts"] = time.monotonic()
        _boot_zmq_cache["ok"] = ok
        _boot_zmq_cache["msg"] = msg
    return ok, msg


@asynccontextmanager
async def _lifespan(app: FastAPI):
    pool = AsyncZmqSimPool(get_rep_url())
    await pool.start()
    app.state.zmq_pool = pool
    try:
        yield
    finally:
        await pool.close()
        app.state.zmq_pool = None


app = FastAPI(title="ngspice kernel demo bridge", version="0.2", lifespan=_lifespan)


@app.get("/api/boot/status")
async def boot_status() -> dict:
    ok, step = await refresh_zmq_boot_status()
    return {
        "ready": ok,
        "current_step": step,
        "rep_url": get_rep_url(),
        "pub_url": get_pub_url(),
        "checks": [],
        "progress": 1.0 if ok else 0.0,
    }


@app.get("/api/server/stats")
async def server_stats(request: Request) -> dict[str, Any]:
    """Proxy ``WIRE_STATS`` from ``ngspice-server`` (protobuf ``ServerStats``)."""
    pool: AsyncZmqSimPool = request.app.state.zmq_pool
    st = await pool.fetch_server_stats()
    return MessageToDict(st, preserving_proto_field_name=True)


@app.get("/metrics")
async def metrics() -> Response:
    if not _prometheus_enabled():
        raise HTTPException(status_code=404, detail="Prometheus metrics disabled or prometheus_client missing")
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)


async def _simulate_via_pool(
    request: Request,
    *,
    netlist: str,
    analysis: str,
    timeout_sec: float,
    request_id: str,
    stream_diagnostics: bool,
) -> SimResult:
    pool: AsyncZmqSimPool | None = getattr(request.app.state, "zmq_pool", None)
    if pool is not None:
        return await pool.simulate(
            netlist,
            analysis=analysis,
            timeout_sec=timeout_sec,
            request_id=request_id,
            stream_diagnostics=stream_diagnostics,
        )

    def _run() -> SimResult:
        with NgspiceClient(get_rep_url()) as c:
            return c.simulate(
                netlist,
                analysis=analysis,
                timeout_sec=timeout_sec,
                request_id=request_id,
                stream_diagnostics=stream_diagnostics,
            )

    return await asyncio.to_thread(_run)


@app.get("/api/examples/index")
async def examples_index() -> JSONResponse:
    idx = _EXAMPLES / "index.json"
    if not idx.is_file():
        raise HTTPException(status_code=404, detail="examples/index.json missing")
    import json

    return JSONResponse(content=json.loads(idx.read_text(encoding="utf-8")))


@app.get("/api/examples/circuit")
async def examples_circuit(path: str = Query(...)) -> dict[str, str]:
    f = _safe_example_path(path)
    if f.suffix.lower() != ".cir" or not f.is_file():
        raise HTTPException(status_code=404, detail="circuit file not found")
    return {"text": f.read_text(encoding="utf-8", errors="replace")}


@app.post("/api/parse-netlist")
async def parse_netlist(req: ParseBody) -> dict:
    """Rough component count for DRC panel (full SPICE parse not required for DC OP demo)."""
    text = req.text or ""
    components: list[dict] = []
    models: dict[str, dict] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("*") or line.startswith("."):
            if line.upper().startswith(".MODEL"):
                parts = line.split()
                if len(parts) >= 2:
                    models[parts[1]] = {}
            continue
        m = re.match(
            r"^([A-Za-z][A-Za-z0-9_]*)\s+(\S+)\s+(\S+)\s+(.+)$",
            line,
        )
        if not m:
            continue
        cid, n1, n2, rest = m.group(1), m.group(2), m.group(3), m.group(4)
        letter = cid[0].upper()
        if letter not in "RLCVIEGFHDMQJ":
            continue
        val = 0.0
        tok = rest.split()[0] if rest.split() else ""
        try:
            val = float(tok)
        except ValueError:
            val = 0.0
        components.append(
            {
                "id": cid,
                "type": letter,
                "node1": n1,
                "node2": n2,
                "value": val,
                "phase": 0.0,
                "ctrl_n1": "",
                "ctrl_n2": "",
                "ctrl_n3": "",
                "ctrl_source": "",
                "model_params": None,
                "spec": "",
                "value_str": "",
                "model_name": "",
                "port_nodes": [],
                "subckt_name": "",
                "instance_params": {},
            }
        )
    return {"components": components, "models": models}


@app.get("/api/components/count-by-type")
async def count_by_type() -> dict:
    return {"total": 0, "by_type": []}


@app.post("/api/components/search")
async def components_search(_body: ComponentSearchBody) -> dict:
    return {"results": []}


@app.get("/api/components/{part_number}")
async def component_detail(part_number: str) -> dict:
    """``libraryCache.getPartDetail`` — catalog not bundled; always unknown."""
    _ = part_number
    raise HTTPException(status_code=404, detail="part not in demo catalog")


@app.post("/api/ai/generate")
async def ai_generate(_req: AIRequest) -> dict:
    raise HTTPException(
        status_code=503,
        detail="AI generate is not enabled in the ngspice kernel demo bridge",
    )


@app.post("/api/simulate")
async def simulate(request: Request, body: SimulateBody) -> dict:
    net = (body.netlist_text or "").strip()
    if not net:
        raise HTTPException(status_code=422, detail="empty netlist_text")
    an = (body.analysis_type or "op").strip().lower()
    if an not in ("op", "ac", "tran", "dc"):
        an = "op"

    req_id = str(uuid.uuid4())
    collector = DiagCollector(get_pub_url(), req_id)
    collector.start()
    await asyncio.sleep(0.02)

    out: dict | None = None
    metric_result = "error"
    try:
        if an == "tran":
            zmq_err = ""
            try:
                ok_z, tr_z, zmq_err = await simulate_transient_async(
                    net,
                    pool=request.app.state.zmq_pool,
                    timeout_sec=120.0,
                    request_id=req_id,
                    stream_diagnostics=True,
                )
            except NgspiceTimeoutError as e:
                ok_z, tr_z, zmq_err = False, None, str(e)
            except NgspiceServerError as e:
                ok_z, tr_z, zmq_err = False, None, str(e)

            if zmq_err == "SERVER_BUSY":
                metric_result = "busy"
                raise HTTPException(
                    status_code=503,
                    detail="ngspice-server busy (all workers and queue full); retry shortly",
                    headers={"Retry-After": "1"},
                )

            if ok_z and tr_z is not None:
                wall_ms = float(tr_z.pop("_wall_ms", 0.0))
                out = _tran_cli_response(
                    tr_z, wall_ms=wall_ms, analysis_type=an, solver_name="ngspice-zmq-tran"
                )
            else:
                ok_cli, tr_cli, cli_msg = run_transient(net)
                if ok_cli and tr_cli is not None:
                    wall_ms = float(tr_cli.pop("_wall_ms", 0.0))
                    out = _tran_cli_response(tr_cli, wall_ms=wall_ms, analysis_type=an)
                    if zmq_err:
                        out["warnings"] = [
                            f"ZMQ transient unavailable ({zmq_err}); used batch ngspice."
                        ] + list(out["warnings"])
                else:
                    try:
                        res = await _simulate_via_pool(
                            request,
                            netlist=net,
                            analysis="op",
                            timeout_sec=60.0,
                            request_id=req_id,
                            stream_diagnostics=True,
                        )
                    except NgspiceTimeoutError as e:
                        metric_result = "timeout"
                        raise HTTPException(status_code=504, detail=str(e)) from e
                    except NgspiceServerError as e:
                        raise HTTPException(status_code=502, detail=str(e)) from e
                    if res.error == SimResult.ErrorCode.SERVER_BUSY:
                        metric_result = "busy"
                        raise HTTPException(
                            status_code=503,
                            detail="ngspice-server busy (all workers and queue full); retry shortly",
                            headers={"Retry-After": "1"},
                        )
                    out = _sim_to_simulation_response(res, analysis_type=an)
                    parts = [p for p in (zmq_err, cli_msg) if p]
                    hint = "; ".join(parts) if parts else "transient failed"
                    out["warnings"] = [hint] + list(out["warnings"])
                    out["transient"] = None
        else:
            try:
                res = await _simulate_via_pool(
                    request,
                    netlist=net,
                    analysis=an,
                    timeout_sec=60.0,
                    request_id=req_id,
                    stream_diagnostics=True,
                )
            except NgspiceTimeoutError as e:
                metric_result = "timeout"
                raise HTTPException(status_code=504, detail=str(e)) from e
            except NgspiceServerError as e:
                raise HTTPException(status_code=502, detail=str(e)) from e
            if res.error == SimResult.ErrorCode.SERVER_BUSY:
                metric_result = "busy"
                raise HTTPException(
                    status_code=503,
                    detail="ngspice-server busy (all workers and queue full); retry shortly",
                    headers={"Retry-After": "1"},
                )
            out = _sim_to_simulation_response(res, analysis_type=an)
        if out is not None:
            metric_result = "ok"
    finally:
        # Brief grace so SUB can receive DiagEvents still in flight after ZMQ reply.
        await asyncio.sleep(0.02)
        collector.stop()
        collector.join(timeout=8.0)
        if out is not None:
            out["diag_events"] = list(collector.events)
        _sim_metric(metric_result)
    if out is None:
        raise HTTPException(status_code=500, detail="simulate produced no response")
    return out
