"""Load and validate chapter_ledger.json."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .constants import LOGGER_NAME, MAX_MISSING_LIST
from .console import step, title, warn
from .exceptions import BookFactoryConfigError, BookFactoryIOError


@dataclass(frozen=True)
class LedgerSourceScanResult:
    """Result of checking every ledger ``files`` path under ``source_root``."""

    chapter_count: int
    file_references: int
    missing: list[tuple[str, str, Path]]  # (ledger_md_key, relative_path, resolved_path)


def scan_ledger_source_files(
    chapter_ledger: dict[str, dict[str, Any]],
    source_root: Path,
) -> LedgerSourceScanResult:
    """Resolve each ``files`` entry against *source_root*; list entries where the file is absent."""
    missing: list[tuple[str, str, Path]] = []
    file_refs = 0
    root = source_root.resolve()
    for md_name, spec in chapter_ledger.items():
        for rel in spec["files"]:
            file_refs += 1
            resolved = (root / rel).resolve()
            if not resolved.is_file():
                missing.append((md_name, rel, resolved))
    return LedgerSourceScanResult(
        chapter_count=len(chapter_ledger),
        file_references=file_refs,
        missing=missing,
    )


def report_ledger_source_scan(result: LedgerSourceScanResult, *, source_root: Path) -> None:
    """Print a ledger/source audit to the console and to the application logger (if configured)."""
    log = logging.getLogger(LOGGER_NAME)
    title("Ledger source file audit")
    step(
        "audit",
        f"source_root={source_root}  chapters={result.chapter_count}  "
        f"file refs={result.file_references}  missing={len(result.missing)}",
    )
    log.info(
        "Ledger source audit: root=%s chapters=%d file_refs=%d missing=%d",
        source_root,
        result.chapter_count,
        result.file_references,
        len(result.missing),
    )
    if not result.missing:
        step("audit", "all referenced source paths exist under source_root")
        log.info("Ledger source audit: no missing files")
        return

    shown = result.missing[:MAX_MISSING_LIST]
    for md_key, rel, abs_path in shown:
        msg = f"{md_key} → missing `{rel}` (expected {abs_path})"
        warn(msg)
        log.warning("Missing source file: chapter=%s rel=%s path=%s", md_key, rel, abs_path)
    extra = len(result.missing) - len(shown)
    if extra > 0:
        tail = f" … and {extra} more missing path(s) (see log file for full list)."
        warn(tail)
        log.warning("Ledger audit: %d additional missing paths not listed on console", extra)
    for md_key, rel, abs_path in result.missing[MAX_MISSING_LIST:]:
        log.warning("Missing source file: chapter=%s rel=%s path=%s", md_key, rel, abs_path)


def require_ledger_sources_exist(result: LedgerSourceScanResult) -> None:
    """Raise BookFactoryConfigError if any ledger path does not resolve to a file."""
    if not result.missing:
        return
    lines = [f"  [{ch}]  {rel}" for ch, rel, _ in result.missing]
    msg = (
        f"{len(result.missing)} source file(s) missing under source_root:\n"
        + "\n".join(lines)
    )
    raise BookFactoryConfigError(msg)


def load_chapter_ledger(ledger_json: Path) -> dict[str, dict[str, Any]]:
    """Return output filename -> {chapter_title, files, research_prompt}."""
    if not ledger_json.is_file():
        raise BookFactoryConfigError(f"Chapter ledger not found: {ledger_json}")

    try:
        with ledger_json.open(encoding="utf-8") as f:
            raw: Any = json.load(f)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BookFactoryIOError(f"Cannot load chapter ledger {ledger_json}: {exc}") from exc

    if not isinstance(raw, dict):
        raise BookFactoryConfigError("Ledger root must be a JSON object.")

    out: dict[str, dict[str, Any]] = {}
    for md_name, spec in raw.items():
        if not isinstance(md_name, str) or not md_name.endswith(".md"):
            raise BookFactoryConfigError(f"Invalid ledger key (expected *.md filename): {md_name!r}")
        if not isinstance(spec, dict):
            raise BookFactoryConfigError(f"Ledger entry {md_name!r} must be a JSON object.")
        for key in ("chapter_title", "files", "research_prompt"):
            if key not in spec:
                raise BookFactoryConfigError(f"Ledger entry {md_name!r} missing required field {key!r}.")
        chapter_title = spec["chapter_title"]
        files = spec["files"]
        prompt = spec["research_prompt"]
        if not isinstance(chapter_title, str) or not chapter_title.strip():
            raise BookFactoryConfigError(f"Ledger entry {md_name!r}: chapter_title must be a non-empty string.")
        if not isinstance(files, list) or not files or not all(isinstance(p, str) for p in files):
            raise BookFactoryConfigError(
                f"Ledger entry {md_name!r}: files must be a non-empty JSON array of strings."
            )
        if not isinstance(prompt, str) or not prompt.strip():
            raise BookFactoryConfigError(f"Ledger entry {md_name!r}: research_prompt must be a non-empty string.")
        out[md_name] = {
            "chapter_title": chapter_title,
            "files": files,
            "research_prompt": prompt,
        }
    return out
