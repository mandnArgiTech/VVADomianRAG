"""Assemble final chapter Markdown and print run summaries."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from crewai import CrewOutput

from .console import line, step, title


def summary_crew_result(result: CrewOutput, md_path: Path, char_count: int) -> None:
    title("Run summary")
    step("done", f"Tasks finished: {len(result.tasks_output)}")
    for i, t in enumerate(result.tasks_output, start=1):
        agent = (t.agent or "?").strip()
        preview = (t.raw or "").replace("\n", " ").strip()
        if len(preview) > 72:
            preview = preview[:69] + "…"
        step(str(i), f"Agent: {agent}")
        if preview:
            step(" ", f"Output preview: {preview}")
    line()
    step("out", f"Markdown saved ({char_count:,} chars):")
    step(" ", str(md_path))
    line()


def markdown_body(result: CrewOutput, chapter_title: str, source_files: list[Path]) -> str:
    """Build final Markdown from the assembler task output."""
    files_bullet = "\n".join(f"- `{f.as_posix()}`" for f in source_files)
    header = (
        f"# {chapter_title}\n\n"
        f"_Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} — "
        "`crewai/ngspice_book_factory.py`_\n\n"
        f"**Source files:**\n{files_bullet}\n\n"
    )
    if result.tasks_output:
        last = result.tasks_output[-1].raw.strip()
        if last:
            return header + last
    body = (result.raw or "").strip()
    if body:
        return header + body + "\n"
    return header + "_(empty)_\n"
