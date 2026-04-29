#!/usr/bin/env python3
"""Validate that every file path in an oracle / chapter ledger JSON resolves under source_root."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Run from repo root: PYTHONPATH=crewai python crewai/scripts/validate_oracle_paths.py ...
# Or from crewai/: PYTHONPATH=. python scripts/validate_oracle_paths.py ...
if __name__ == "__main__" and __package__ is None:
    _crewai = Path(__file__).resolve().parent.parent
    if str(_crewai) not in sys.path:
        sys.path.insert(0, str(_crewai))

from book_factory.ledger import load_chapter_ledger, scan_ledger_source_files  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify every files[] entry in a chapter ledger exists under source_root.",
    )
    parser.add_argument("oracle_json", type=Path, help="Path to oracle_kinematica.json (or chapter_ledger.json)")
    parser.add_argument("source_root", type=Path, help="ArduPilot / source tree root")
    args = parser.parse_args()

    ledger = load_chapter_ledger(args.oracle_json.resolve())
    scan = scan_ledger_source_files(ledger, args.source_root.resolve())
    if scan.missing:
        print(f"MISSING ({len(scan.missing)}):")
        for ch, rel, _ in scan.missing:
            print(f"  [{ch}]  {rel}")
        return 1
    print("All paths resolve.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
