"""Shared constants for the Ngspice book factory (paths, tuning, logger name)."""

from __future__ import annotations

import os
from pathlib import Path

# Directory containing ngspice_book_factory.py, config.yaml, project_prompts.json, …
CREWAI_DIR: Path = Path(__file__).resolve().parent.parent

DEFAULT_SOURCE_ROOT = CREWAI_DIR.parent / "Studio-Portable-RAG" / "Codebase" / "ngspice"
HEARTBEAT_SEC = 20.0
STEP_FINISH_LOG_INTERVAL = 8.0
MAX_REASON_CHARS = 600
MAX_MISSING_LIST = 15

DEEPSEEK_BASE = "https://api.deepseek.com/v1"

USE_FAST_RESEARCH = os.environ.get("CREW_FAST", "").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)

LOGGER_NAME = "ngspice_book_factory"
