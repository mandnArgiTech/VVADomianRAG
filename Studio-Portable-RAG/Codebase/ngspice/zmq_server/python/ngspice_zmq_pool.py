"""Persistent ``zmq.asyncio`` DEALER pool to ``ngspice-server`` (ZMQ ROUTER)."""

from __future__ import annotations

import asyncio
import os
from typing import Optional

import zmq
import zmq.asyncio

from ngspice_client import (
    NgspiceServerError,
    NgspiceTimeoutError,
    WIRE_STATS,
    _pack_sim_request,
    _unpack_sim_result,
)
from ngspice_sim_pb2 import ServerStats, SimRequest, SimResult


def _wire_body_from_parts(parts: list[bytes]) -> bytes:
    if not parts:
        return b""
    if len(parts) >= 2:
        return parts[-1]
    return parts[0]


class AsyncZmqSimPool:
    """Pool of DEALER sockets (fair load spread on ROUTER). Recovers a socket after recv timeout."""

    def __init__(self, router_url: str, *, pool_size: Optional[int] = None) -> None:
        self._url = router_url
        n = pool_size if pool_size is not None else int(os.environ.get("NGSPICE_ZMQ_POOL", "8"))
        self._size = max(1, min(64, n))
        self._ctx: Optional[zmq.asyncio.Context] = None
        self._queue: asyncio.Queue[zmq.asyncio.Socket]
        self._started = False

    async def start(self) -> None:
        if self._started:
            return
        self._ctx = zmq.asyncio.Context()
        self._queue = asyncio.Queue(maxsize=self._size)
        for _ in range(self._size):
            s = self._ctx.socket(zmq.DEALER)
            s.setsockopt(zmq.LINGER, 0)
            s.connect(self._url)
            await self._queue.put(s)
        self._started = True

    async def close(self) -> None:
        if not self._started or not self._ctx:
            return
        while True:
            try:
                s = self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            try:
                s.close(linger=0)
            except Exception:
                pass
        try:
            self._ctx.term()
        except Exception:
            pass
        self._ctx = None
        self._started = False

    async def _recreate_socket(self, bad: zmq.asyncio.Socket) -> zmq.asyncio.Socket:
        try:
            bad.close(linger=0)
        except Exception:
            pass
        assert self._ctx is not None
        s = self._ctx.socket(zmq.DEALER)
        s.setsockopt(zmq.LINGER, 0)
        s.connect(self._url)
        return s

    async def simulate(
        self,
        netlist: str,
        *,
        analysis: str = "op",
        timeout_sec: float = 60.0,
        stream_diagnostics: bool = False,
        request_id: str = "",
    ) -> SimResult:
        if not self._started:
            raise NgspiceServerError("AsyncZmqSimPool not started")
        req = SimRequest()
        req.netlist = netlist or ""
        req.analysis = (analysis or "op").strip().lower()
        req.stream_diagnostics = bool(stream_diagnostics)
        req.request_id = request_id or ""
        payload = _pack_sim_request(req)
        sock = await self._queue.get()
        try:
            await sock.send_multipart([b"", payload])
            parts = await asyncio.wait_for(sock.recv_multipart(), timeout=timeout_sec)
            raw = _wire_body_from_parts(parts)
            return _unpack_sim_result(raw)
        except asyncio.TimeoutError as e:
            sock = await self._recreate_socket(sock)
            raise NgspiceTimeoutError(
                "no reply from ngspice-server within %.1fs (%s)"
                % (timeout_sec, self._url)
            ) from e
        finally:
            await self._queue.put(sock)

    async def fetch_server_stats(self, *, timeout_sec: float = 5.0) -> ServerStats:
        if not self._started:
            raise NgspiceServerError("AsyncZmqSimPool not started")
        sock = await self._queue.get()
        try:
            await sock.send_multipart([b"", bytes([WIRE_STATS])])
            parts = await asyncio.wait_for(sock.recv_multipart(), timeout=timeout_sec)
            raw = _wire_body_from_parts(parts)
            if len(raw) < 2 or raw[0] != WIRE_STATS:
                raise NgspiceServerError("unexpected stats reply wire %r" % (raw[:1],))
            st = ServerStats()
            st.ParseFromString(memoryview(raw)[1:])
            return st
        finally:
            await self._queue.put(sock)
