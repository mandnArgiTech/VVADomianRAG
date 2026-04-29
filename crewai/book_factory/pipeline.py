"""Per-chapter CrewAI pipeline (research → math → code → assemble)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from crewai import Agent, Crew, CrewOutput, Process, Task

try:
    from crewai_tools import FileReadTool
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "ngspice_book_factory requires crewai_tools. Install with:\n"
        "  pip install crewai-tools\n"
    ) from exc

from .constants import HEARTBEAT_SEC, LOGGER_NAME, MAX_MISSING_LIST
from .console import clip_reason, err, line, step, title
from .markdown import markdown_body, summary_crew_result
from .progress import Heartbeat, ProgressState, make_crew_callbacks
from .prompts import ProjectPrompts, format_prompt_template


def run_chapter(
    md_filename: str,
    chapter_data: dict[str, Any],
    algorithm_researcher: Agent,
    technical_author: Agent,
    project_prompts: ProjectPrompts,
    *,
    source_root: Path,
    output_dir: Path,
) -> tuple[bool, str]:
    """Run the four-task pipeline for one chapter.

    Returns (True, "") on success, or (False, reason) with a one-line reason for batch summaries.
    """
    log = logging.getLogger(LOGGER_NAME)
    chapter_title: str = chapter_data["chapter_title"]
    rel_files: list[str] = chapter_data["files"]
    research_prompt: str = chapter_data["research_prompt"]

    title(f"Chapter: {chapter_title}")
    step("cfg", f"Output file: {md_filename}")
    log.info("Starting chapter %s (%s)", chapter_title, md_filename)

    abs_files: list[Path] = []
    missing: list[str] = []
    for rel in rel_files:
        p = (source_root / rel).resolve()
        if p.is_file():
            abs_files.append(p)
        else:
            missing.append(rel)

    if missing:
        for m in missing:
            err(f"Source file not found: {source_root / m}")
            log.error("Missing source: %s", source_root / m)
        step("skip", f"Skipping chapter — {len(missing)} source file(s) missing")
        shown = missing[:MAX_MISSING_LIST]
        tail = "" if len(missing) <= MAX_MISSING_LIST else f" (+{len(missing) - MAX_MISSING_LIST} more)"
        reason = (
            f"{len(missing)} source path(s) missing under source root "
            f"({source_root}): " + "; ".join(shown) + tail
        )
        return False, clip_reason(reason)

    for f in abs_files:
        step("cfg", f"Source: {f.relative_to(source_root).as_posix()}")

    tools = [FileReadTool(file_path=str(f)) for f in abs_files]
    algorithm_researcher.tools = tools

    filenames_str = ", ".join(f"`{f.name}`" for f in abs_files)
    pp = project_prompts
    tpl_ctx = dict(filenames_str=filenames_str, chapter_title=chapter_title)

    head, tail = pp.research.description.split("{research_prompt}", 1)
    research_description = (
        format_prompt_template("tasks.research.description", head, **tpl_ctx)
        + research_prompt
        + format_prompt_template("tasks.research.description", tail, **tpl_ctx)
    )
    research_task = Task(
        description=research_description,
        expected_output=pp.research.expected_output,
        agent=algorithm_researcher,
    )

    write_math_task = Task(
        description=format_prompt_template(
            "tasks.write_math.description",
            pp.write_math.description,
            **tpl_ctx,
        ),
        expected_output=pp.write_math.expected_output,
        agent=technical_author,
        context=[research_task],
    )

    write_code_task = Task(
        description=format_prompt_template(
            "tasks.write_code.description",
            pp.write_code.description,
            **tpl_ctx,
        ),
        expected_output=pp.write_code.expected_output,
        agent=technical_author,
        context=[research_task],
    )

    assemble_chapter_task = Task(
        description=format_prompt_template(
            "tasks.assemble.description",
            pp.assemble.description,
            **tpl_ctx,
        ),
        expected_output=pp.assemble.expected_output,
        agent=technical_author,
        context=[write_math_task, write_code_task],
    )

    progress = ProgressState()
    task_cb, step_cb = make_crew_callbacks(progress)

    crew = Crew(
        agents=[algorithm_researcher, technical_author],
        tasks=[research_task, write_math_task, write_code_task, assemble_chapter_task],
        process=Process.sequential,
        verbose=False,
        planning=False,
        step_callback=step_cb,
        task_callback=task_cb,
    )

    line()
    step("run", "research → math MD → code MD → assemble final chapter …")
    line()

    heartbeat = Heartbeat(HEARTBEAT_SEC)
    heartbeat.start()
    try:
        result = crew.kickoff()
    except Exception as exc:
        title("Crew run failed")
        err(f"{type(exc).__name__}: {exc}")
        step("hint", "Check API key, network, and DeepSeek service status.")
        log.exception("Crew kickoff failed for %s", md_filename)
        reason = f"Crew kickoff failed: {type(exc).__name__}: {exc}"
        return False, clip_reason(reason)
    finally:
        heartbeat.stop()

    if not isinstance(result, CrewOutput):
        err(f"kickoff() returned {type(result)!r}, expected CrewOutput.")
        log.error("kickoff returned %s, expected CrewOutput", type(result).__name__)
        reason = f"Crew kickoff returned {type(result).__name__}, expected CrewOutput"
        return False, clip_reason(reason)

    md_path = (output_dir / md_filename).resolve()
    md_text = markdown_body(result, chapter_title, abs_files)
    try:
        md_path.write_text(md_text, encoding="utf-8")
    except OSError as exc:
        err(f"Could not write Markdown to {md_path}: {exc}")
        log.exception("Could not write output %s", md_path)
        reason = f"Could not write output {md_path}: {exc}"
        return False, clip_reason(reason)

    summary_crew_result(result, md_path, len(md_text))
    log.info("Chapter written: %s (%d chars)", md_path, len(md_text))
    return True, ""
