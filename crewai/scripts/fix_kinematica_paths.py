#!/usr/bin/env python3
"""
One-shot migration: repair relative paths in oracle_kinematica.json so every file exists
under a given ArduPilot source_root. Uses filesystem search + disambiguation rules.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable

if __name__ == "__main__" and __package__ is None:
    _crewai = Path(__file__).resolve().parent.parent
    if str(_crewai) not in sys.path:
        sys.path.insert(0, str(_crewai))

from book_factory.ledger import load_chapter_ledger  # noqa: E402

# Chapter 055: AP_MotorsUGV removed upstream — use matrix mixer (closest documented mixer core).
_CH055 = "Chapter_055_UGV_Motor_Mixer_and_Skid_Steering_Kinematics.md"
# Chapter 129: root tests/*.cpp were removed; gtests live under libraries/*/tests/.
_CH129 = "Chapter_129_Waf_Build_System_and_GTest_Unit_Infrastructure.md"
# Chapter 149: libraries/AP_DDS only exists on newer master; use UAVCAN + MAVLink as portable stand-ins for companion-bus extraction on older branches.
_CH149 = "Chapter_149_ROS_2_DDS_Integration_and_Micro_XRCE_Offloading.md"
FULL_CHAPTER_FILES_OVERRIDE: dict[str, list[str]] = {
    _CH055: [
        "libraries/AP_Motors/AP_MotorsMatrix.cpp",
        "libraries/AP_Motors/AP_MotorsMatrix.h",
    ],
    _CH129: [
        "wscript",
        "Tools/ardupilotwaf/boards.py",
        "Tools/ardupilotwaf/chibios.py",
        "libraries/AP_Math/tests/test_math.cpp",
        # Obsolete tests/test_ekf.cpp — no longer in tree; quaternion tests cover nav math regression checks.
        "libraries/AP_Math/tests/test_quaternion.cpp",
    ],
    _CH149: [
        "libraries/AP_UAVCAN/AP_UAVCAN.cpp",
        "modules/mavlink/message_definitions/v1.0/common.xml",
    ],
}

_EXACT_REL_OVERRIDES: dict[str, str] = {
    "Tools/LogAnalyzer/tests/TestEKF.py": "Tools/LogAnalyzer/tests/TestIMUMatch.py",
    "libraries/AP_IRLock/AP_IRLock.cpp": "libraries/AP_IRLock/IRLock.cpp",
    # Ledger mistakenly listed a directory; pick a representative applet script.
    "libraries/AP_Scripting/applets/": "libraries/AP_Scripting/applets/MissionSelector.lua",
    # ROMFS embedding script renamed (Rover 4.2 era vs master docs).
    "Tools/ardupilotwaf/romfs.py": "Tools/ardupilotwaf/embed.py",
}

# Rule 3 — LogStructure.h location depends on chapter primary library (story STORY M5).
_LOG_STRUCTURE_BY_CHAPTER: dict[str, str] = {
    "Chapter_089_EKF_Core_Infrastructure_Buffers_and_GSF_Yaw.md": "libraries/AP_NavEKF/LogStructure.h",
    "Chapter_100_Core_Energy_Arbitration_and_Analog_ADC_Scaling.md": "libraries/AP_BattMonitor/LogStructure.h",
    "Chapter_103_ESC_Telemetry_RPM_Tracking_and_Motor_Diagnostics.md": "libraries/AP_ESC_Telem/LogStructure.h",
    "Chapter_105_EKF2_Core_Covariance_and_IMU_Bias_Tracking.md": "libraries/AP_NavEKF2/LogStructure.h",
    "Chapter_117_Photogrammetry_Shutter_Triggering_and_Serial_Camera_Payloads.md": "libraries/AP_Camera/LogStructure.h",
}

# Prefer this subdirectory when multiple Models/*/File.m exist (EKF derivation canon).
_NAV_MATLAB_PREF_ORDER: tuple[str, ...] = (
    "GimbalEstimatorExample",
    "QuaternionMathExample",
    "AttErrVecMathExample",
)

# Upstream renames (basename → search name if former missing).
_BASENAME_ALIASES: dict[str, str] = {
    "AP_HAL.cpp": "HAL.cpp",
}


def _collect_by_basename(root: Path, name: str) -> list[Path]:
    # rglob is slower than subprocess find on huge trees; acceptable for one-shot migration.
    return sorted({p for p in root.rglob(name) if p.is_file()})


def _pick_best(candidates: Iterable[Path], root: Path, *, chapter_key: str, original_rel: str) -> Path:
    cands = list(candidates)
    if not cands:
        raise FileNotFoundError(f"No file {original_rel!r} (basename) under {root}")
    if len(cands) == 1:
        return cands[0]

    base = Path(original_rel).name

    # Root wscript only (Chapter_129 mixed chapter).
    if base == "wscript" and original_rel == "wscript":
        rp = root / "wscript"
        if rp.is_file():
            return rp.resolve()

    # LogStructure.h resolved via chapter map elsewhere — should not hit multi here often.
    if base == "LogStructure.h":
        p = root / _LOG_STRUCTURE_BY_CHAPTER.get(chapter_key, "")
        if p.is_file():
            return p.resolve()

    # MATLAB under AP_NavEKF/Models: prefer pref order subfolders.
    scored: list[tuple[tuple[int, int], Path]] = []
    for p in cands:
        ps = p.as_posix()
        sub_rank = 99
        for i, sub in enumerate(_NAV_MATLAB_PREF_ORDER):
            if f"/Models/{sub}/" in ps:
                sub_rank = i
                break
        # Prefer libraries/AP_* over vehicle trees.
        lib_rank = 0 if "/libraries/AP_" in ps else (1 if "/libraries/" in ps else 2)
        scored.append(((lib_rank, sub_rank), p))
    scored.sort(key=lambda x: (x[0][0], x[0][1], len(x[1].parts), x[1].as_posix()))
    return scored[0][1]


def resolve_file(root: Path, chapter_key: str, rel: str) -> str:
    root = root.resolve()
    rel = _EXACT_REL_OVERRIDES.get(rel, rel)
    rel_path = Path(rel)
    direct = (root / rel_path).resolve()
    try:
        direct.relative_to(root)
    except ValueError:
        pass
    else:
        if direct.is_file():
            return rel

    name = rel_path.name

    if name == "LogStructure.h" and chapter_key in _LOG_STRUCTURE_BY_CHAPTER:
        candidate = root / _LOG_STRUCTURE_BY_CHAPTER[chapter_key]
        if candidate.is_file():
            return _LOG_STRUCTURE_BY_CHAPTER[chapter_key]

    matches = _collect_by_basename(root, name)
    if not matches and name in _BASENAME_ALIASES:
        matches = _collect_by_basename(root, _BASENAME_ALIASES[name])
    # Case / rename: same directory as stale path (e.g. loganalyzer.py → LogAnalyzer.py).
    if not matches and "/" in rel:
        parent = (root / Path(rel).parent).resolve()
        if parent.is_dir():
            for c in parent.iterdir():
                if c.is_file() and c.name.lower() == name.lower():
                    return c.relative_to(root).as_posix()
    best = _pick_best(matches, root, chapter_key=chapter_key, original_rel=rel)
    out = best.relative_to(root).as_posix()
    if Path(out).as_posix() != Path(rel).as_posix():
        pass  # resolved
    return out


def migrate_oracle(oracle_path: Path, source_root: Path, *, dry_run: bool = False) -> None:
    source_root = source_root.resolve()
    data = load_chapter_ledger(oracle_path)

    new_data: dict[str, dict] = {}
    for chapter_key, spec in data.items():
        if chapter_key in FULL_CHAPTER_FILES_OVERRIDE:
            files = list(FULL_CHAPTER_FILES_OVERRIDE[chapter_key])
        else:
            files = []
            for rel in spec["files"]:
                if (source_root / rel).is_file():
                    files.append(Path(rel).as_posix())
                    continue
                files.append(resolve_file(source_root, chapter_key, rel))
        new_data[chapter_key] = {
            "chapter_title": spec["chapter_title"],
            "files": files,
            "research_prompt": spec["research_prompt"],
        }

    # Verify all exist
    missing: list[tuple[str, str]] = []
    for chapter_key, spec in new_data.items():
        for rel in spec["files"]:
            if not (source_root / rel).is_file():
                missing.append((chapter_key, rel))
    if missing:
        msg = "Still missing after migration:\n" + "\n".join(f"  [{a}] {b}" for a, b in missing)
        raise SystemExit(msg)

    if dry_run:
        print(json.dumps(new_data, indent=2)[:2000], "...")
        return

    oracle_path.write_text(json.dumps(new_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {oracle_path} ({len(new_data)} chapters).")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "oracle_json",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "oracle_kinematica.json",
        help="Path to oracle_kinematica.json (default: crewai/oracle_kinematica.json)",
    )
    p.add_argument(
        "source_root",
        nargs="?",
        type=Path,
        default=None,
        help="ArduPilot checkout root (default: ../../Studio-Portable-RAG/Codebase/ardupilot from crewai/)",
    )
    p.add_argument("--dry-run", action="store_true", help="Print sample JSON only; do not write")
    args = p.parse_args()

    root = args.source_root
    if root is None:
        candidate = Path(__file__).resolve().parent.parent.parent / "Studio-Portable-RAG" / "Codebase" / "ardupilot"
        root = candidate if candidate.is_dir() else Path.cwd()
    if not root.is_dir():
        print(f"Not a directory: {root}", file=sys.stderr)
        return 2

    migrate_oracle(args.oracle_json.resolve(), root, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
