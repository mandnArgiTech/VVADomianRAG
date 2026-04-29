"""Configure the named application logger (file handler, no propagation noise)."""

from __future__ import annotations

import logging
from pathlib import Path

from .constants import LOGGER_NAME

_configured = False


def configure_logging(log_file: Path | None, level: int) -> logging.Logger:
    """Attach a UTF-8 file handler when *log_file* is set; idempotent for repeated calls.

    The logger does not propagate to the root logger, so library use does not
    duplicate messages on the root console handler.
    """
    global _configured
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = False

    if _configured:
        return logger

    fmt = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_file, encoding="utf-8", mode="a")
        fh.setLevel(level)
        fh.setFormatter(fmt)
        logger.addHandler(fh)

    _configured = True
    return logger
