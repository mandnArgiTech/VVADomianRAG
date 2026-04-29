"""Heartbeat thread and CrewAI step/task callbacks (progress UX)."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any

from crewai.agents.parser import AgentAction, AgentFinish
from crewai.tasks.task_output import TaskOutput

from .constants import HEARTBEAT_SEC, STEP_FINISH_LOG_INTERVAL
from .console import step


@dataclass
class ProgressState:
    """Throttled logging state for AgentFinish callbacks."""

    last_finish_log_mono: float | None = None


def make_crew_callbacks(progress: ProgressState):
    """Build (task_callback, step_callback) for a Crew."""

    def task_callback(output: TaskOutput) -> None:
        agent = (output.agent or "?").strip()
        nchars = len(output.raw or "")
        desc = (output.description or "").replace("\n", " ").strip()
        if len(desc) > 52:
            desc = desc[:49] + "…"
        step("task", f"completed — agent={agent!r}, {nchars:,} chars — {desc}")

    def step_callback(payload: Any) -> None:
        if isinstance(payload, AgentAction):
            inp = payload.tool_input or ""
            inp_note = f"{len(inp)} chars" if inp else "empty"
            step("tool", f"{payload.tool} ({inp_note})")
            return
        if isinstance(payload, AgentFinish):
            now = time.monotonic()
            prev = progress.last_finish_log_mono
            if prev is None or (now - prev) >= STEP_FINISH_LOG_INTERVAL:
                progress.last_finish_log_mono = now
                out = payload.output
                body = out if isinstance(out, str) else str(out)
                step("live", f"model output segment ({len(body):,} chars)")
            return
        step("live", f"step: {type(payload).__name__}")

    return task_callback, step_callback


class Heartbeat:
    """Background thread: periodic lines so a long LLM call does not look frozen."""

    def __init__(self, interval_sec: float = HEARTBEAT_SEC) -> None:
        self._interval = max(0.0, interval_sec)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._t0 = time.monotonic()

    def start(self) -> None:
        if self._interval <= 0:
            return

        def _run() -> None:
            tick = 0
            while not self._stop.wait(self._interval):
                tick += 1
                elapsed = int(time.monotonic() - self._t0)
                step("…", f"heartbeat #{tick} — crew still running ({elapsed}s elapsed)")

        self._thread = threading.Thread(
            target=_run,
            name="ngspice-book-heartbeat",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=3.0)
