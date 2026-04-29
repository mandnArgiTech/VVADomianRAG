"""CLI entry: argument parsing, config merge, logging, batch loop."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from crewai import Agent

from .config import parse_yaml_file, resolve_book_factory_settings
from .constants import CREWAI_DIR, LOGGER_NAME, USE_FAST_RESEARCH
from .console import err, line, step, title, warn
from .exceptions import BookFactoryError, BookFactoryConfigError, BookFactoryIOError
from .ledger import (
    load_chapter_ledger,
    report_ledger_source_scan,
    require_ledger_sources_exist,
    scan_ledger_source_files,
)
from .llm import build_llms
from .logging_setup import configure_logging
from .pipeline import run_chapter
from .prompts import load_project_prompts, validate_research_template
from .schemas import validate_oracle, validate_project_prompts


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate Ngspice book chapters from a JSON ledger and C sources. "
            "Configure paths, project_prompts.json, log_file, and API key via "
            "crewai/config.yaml (auto-loaded if present), environment variables, "
            "and/or CLI flags (CLI wins)."
        ),
    )
    parser.add_argument(
        "chapters",
        nargs="*",
        help=(
            "Specific chapter filenames to generate (e.g., Chapter_01.md). "
            "If none provided, runs the entire ledger."
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing markdown files instead of skipping them.",
    )
    parser.add_argument(
        "--config",
        "-c",
        type=Path,
        default=None,
        help=(
            "YAML config file. If omitted and crewai/config.yaml exists next to the "
            "entry script, that file is loaded automatically."
        ),
    )
    parser.add_argument(
        "--source-root",
        "--ngspice-root",
        dest="source_root",
        type=Path,
        help="Root directory of the Ngspice (or C source) tree containing ledger paths.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory where generated chapter Markdown files are written.",
    )
    parser.add_argument(
        "--ledger",
        type=Path,
        help="Path to chapter_ledger.json (or equivalent) listing chapters and source files.",
    )
    parser.add_argument(
        "--project-prompts",
        type=Path,
        help=(
            "Path to project_prompts.json (agent roles and task templates). "
            "Default: crewai/project_prompts.json next to the entry script."
        ),
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=argparse.SUPPRESS,
        help="Append log messages to this file (UTF-8). Overrides config and NGSPICE_BOOK_LOG_FILE.",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default=argparse.SUPPRESS,
        help="Logging level (e.g. DEBUG, INFO). Overrides config and NGSPICE_BOOK_LOG_LEVEL.",
    )
    parser.add_argument(
        "--deepseek-api-key",
        dest="deepseek_api_key",
        default=argparse.SUPPRESS,
        help="DeepSeek API key (overrides YAML and environment). Prefer env DEEPSEEK_API_KEY.",
    )
    return parser


def load_yaml_config(args: argparse.Namespace) -> tuple[Path | None, dict]:
    """Resolve YAML path: explicit --config, else auto ``crewai/config.yaml`` if present."""
    if getattr(args, "config", None) is not None:
        p = Path(args.config).expanduser().resolve()
        return p, parse_yaml_file(p)
    auto = CREWAI_DIR / "config.yaml"
    if auto.is_file():
        return auto, parse_yaml_file(auto)
    return None, {}


def _validate_inputs(
    oracle: dict,
    prompts: dict,
    *,
    oracle_name: str,
    prompts_name: str,
) -> None:
    errors: list[str] = []
    errors += validate_oracle(oracle, name=oracle_name)
    errors += validate_project_prompts(prompts, name=prompts_name)
    if errors:
        log = logging.getLogger(LOGGER_NAME)
        log.error("Configuration validation failed (%d issues):", len(errors))
        for e in errors:
            log.error("  %s", e)
        raise SystemExit(2)


def main() -> None:
    script_dir = CREWAI_DIR
    parser = build_arg_parser()
    args = parser.parse_args()

    try:
        yaml_path, yaml_data = load_yaml_config(args)
        cfg = resolve_book_factory_settings(
            script_dir=script_dir,
            yaml_path=yaml_path,
            yaml_data=yaml_data,
            args=args,
        )
    except BookFactoryError as e:
        title("Configuration error")
        err(str(e))
        raise SystemExit(e.exit_code) from e

    configure_logging(cfg.log_file, cfg.log_level)
    log = logging.getLogger(LOGGER_NAME)

    try:
        if not cfg.source_root.is_dir():
            raise BookFactoryConfigError(f"Source root is not a directory:\n  {cfg.source_root}")
        if not cfg.api_key.strip():
            raise BookFactoryConfigError(
                "No DeepSeek API key configured. Set deepseek_api_key in YAML, use "
                "--deepseek-api-key, or set DEEPSEEK_API_KEY / OPENAI_API_KEY in the environment."
            )

        os.environ.setdefault("OPENAI_API_KEY", cfg.api_key.strip())

        try:
            cfg.output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise BookFactoryIOError(f"Cannot create output dir {cfg.output_dir}: {exc}") from exc

        chapter_ledger = load_chapter_ledger(cfg.ledger_json)

        if args.chapters:
            unknown = [name for name in args.chapters if name not in chapter_ledger]
            if unknown:
                raise BookFactoryConfigError(
                    "Chapter(s) not in ledger: " + ", ".join(repr(n) for n in unknown)
                )

            chapter_ledger = {name: chapter_ledger[name] for name in args.chapters}

        prompts_raw = json.loads(cfg.prompts_json.read_text(encoding="utf-8"))
        _validate_inputs(
            chapter_ledger,
            prompts_raw,
            oracle_name=cfg.ledger_json.name,
            prompts_name=cfg.prompts_json.name,
        )

        ledger_scan = scan_ledger_source_files(chapter_ledger, cfg.source_root)
        report_ledger_source_scan(ledger_scan, source_root=cfg.source_root)
        require_ledger_sources_exist(ledger_scan)

        project_prompts = load_project_prompts(cfg.prompts_json)
        validate_research_template(project_prompts)

        _reasoner_llm, chat_llm, research_llm = build_llms(cfg.api_key.strip())

        arp = project_prompts.algorithm_researcher
        tap = project_prompts.technical_author
        algorithm_researcher = Agent(
            role=arp.role,
            goal=arp.goal,
            backstory=arp.backstory,
            verbose=False,
            allow_delegation=False,
            llm=research_llm,
            tools=[],
        )
        technical_author = Agent(
            role=tap.role,
            goal=tap.goal,
            backstory=tap.backstory,
            verbose=False,
            allow_delegation=False,
            llm=chat_llm,
        )

        title("Ngspice Book Factory — batch mode")
        if yaml_path is not None:
            step("cfg", f"Config file  : {yaml_path}")
            step("cfg", "YAML keys/types validated (unknown keys rejected)")
            log.info("YAML config validated: %s", yaml_path)
        step("cfg", f"Source root  : {cfg.source_root}")
        step("cfg", f"Output dir   : {cfg.output_dir}")
        step("cfg", f"Ledger file  : {cfg.ledger_json}")
        step("cfg", f"Prompts file : {cfg.prompts_json}")
        if cfg.log_file is not None:
            step("cfg", f"Log file     : {cfg.log_file}")
        step("cfg", f"Log level    : {logging.getLevelName(cfg.log_level)}")
        step("cfg", f"Chapters     : {len(chapter_ledger)}")
        if USE_FAST_RESEARCH:
            step("cfg", "CREW_FAST=1 → researcher uses deepseek-chat")
        else:
            step("cfg", "Researcher uses deepseek-reasoner (long API gaps are normal)")
        line()

        written = 0
        skipped = 0
        failed = 0
        failure_log: list[tuple[str, str]] = []

        for md_filename, chapter_data in chapter_ledger.items():
            md_path = cfg.output_dir / md_filename
            if md_path.exists() and not args.force:
                step("skip", f"Chapter already generated: {md_filename}")
                skipped += 1
                continue
            if md_path.exists() and args.force:
                step("force", f"Overwriting existing output: {md_filename}")

            try:
                ok, fail_reason = run_chapter(
                    md_filename,
                    chapter_data,
                    algorithm_researcher,
                    technical_author,
                    project_prompts,
                    source_root=cfg.source_root,
                    output_dir=cfg.output_dir,
                )
            except KeyboardInterrupt:
                title("Interrupted")
                warn("KeyboardInterrupt — batch cancelled by user.")
                step("stat", f"Written so far: {written}, skipped: {skipped}, failed: {failed}")
                raise SystemExit(130) from None
            except BookFactoryError as e:
                log.error("Chapter %s aborted: %s", md_filename, e)
                title("Chapter error")
                err(str(e))
                raise SystemExit(e.exit_code) from e
            except Exception:
                log.exception("Unexpected error while running chapter %s", md_filename)
                title("Fatal error")
                err(f"Unexpected error while processing {md_filename}; see log file for details.")
                raise SystemExit(1) from None

            if ok:
                written += 1
            else:
                failed += 1
                failure_log.append((md_filename, fail_reason or "(no reason recorded)"))

        title("Batch complete")
        step("stat", f"Written: {written}  |  Skipped: {skipped}  |  Failed: {failed}")
        if failure_log:
            title("Failures (chapter → reason)")
            for md_name, reason in failure_log:
                step("fail", md_name)
                step("reason", reason)
        line()
        log.info("Batch finished: written=%d skipped=%d failed=%d", written, skipped, failed)

    except BookFactoryError as e:
        log.error("%s", e)
        title("Configuration error")
        err(str(e))
        raise SystemExit(e.exit_code) from e
    except SystemExit:
        raise
    except Exception:
        log.exception("Fatal error in book factory main")
        title("Fatal error")
        err("Unexpected failure; see log file for details if configured.")
        raise SystemExit(1) from None


if __name__ == "__main__":  # pragma: no cover
    main()
