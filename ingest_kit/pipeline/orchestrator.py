"""Thin wrapper so CLI can call ingestion without circular imports at module load."""

from __future__ import annotations

import argparse


def ingest_run(args: argparse.Namespace) -> int:
    import ingest as m

    return m._ingest_run_impl(args)
