"""Standalone validator — run before commit to catch oracle / prompt regressions."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_CREWAI = Path(__file__).resolve().parent.parent
if str(_CREWAI) not in sys.path:
    sys.path.insert(0, str(_CREWAI))

from book_factory.schemas import validate_oracle, validate_project_prompts  # noqa: E402


def main() -> int:
    base = _CREWAI
    targets = {
        "chapter_ledger.json": validate_oracle,
        "oracle_kinematica.json": validate_oracle,
        "oracle_physics.json": validate_oracle,
        "project_prompts_ngspice.json": validate_project_prompts,
        "project_prompts_kinematica.json": validate_project_prompts,
    }
    fail = 0
    for filename, validator in targets.items():
        path = base / filename
        if not path.exists():
            print(f"  SKIP {filename} (not present)")
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        errors = validator(data, name=filename)
        if errors:
            fail += 1
            print(f"\n=== {filename}: {len(errors)} issue(s) ===")
            for e in errors:
                print(f"  {e}")
        else:
            print(f"  OK   {filename}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
