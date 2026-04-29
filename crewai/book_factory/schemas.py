"""JSON Schema validation for oracle / project_prompts / ledger inputs."""

from __future__ import annotations

import re
from typing import Any

# Chapter key pattern: Chapter_NNN_<slug>.md (2–3 digit zero-padded chapter index)
CHAPTER_KEY_RE = re.compile(r"^Chapter_(\d{2,3})_[A-Za-z0-9_]+\.md$")

ORACLE_REQUIRED_FIELDS = frozenset({"chapter_title", "files", "research_prompt"})

PROMPT_REQUIRED_AGENTS = frozenset({"algorithm_researcher", "technical_author"})
PROMPT_REQUIRED_TASKS = frozenset({"research", "write_math", "write_code", "assemble"})
PROMPT_AGENT_FIELDS = frozenset({"role", "goal", "backstory"})
PROMPT_TASK_FIELDS = frozenset({"description", "expected_output"})

# Placeholders that the pipeline supplies via .format()
ALLOWED_PLACEHOLDERS = frozenset({"filenames_str", "research_prompt", "chapter_title"})


class SchemaError(ValueError):
    """Structured validation failure (optional caller use)."""


def validate_oracle(data: Any, *, name: str = "oracle") -> list[str]:
    """Return a list of error strings; empty list means valid."""
    errors: list[str] = []
    if not isinstance(data, dict):
        return [f"{name}: top-level must be an object, got {type(data).__name__}"]
    if not data:
        return [f"{name}: contains zero chapters"]

    seen_numbers: dict[int, str] = {}
    for ch_key, ch in data.items():
        m = CHAPTER_KEY_RE.match(ch_key)
        if not m:
            errors.append(f"{name}[{ch_key}]: key does not match Chapter_NNN_<slug>.md")
            continue
        num = int(m.group(1))
        if num in seen_numbers:
            errors.append(
                f"{name}[{ch_key}]: duplicate chapter number {num} (also in {seen_numbers[num]})"
            )
        seen_numbers[num] = ch_key

        if not isinstance(ch, dict):
            errors.append(f"{name}[{ch_key}]: value must be object")
            continue
        missing = ORACLE_REQUIRED_FIELDS - set(ch.keys())
        if missing:
            errors.append(f"{name}[{ch_key}]: missing fields {sorted(missing)}")
            continue
        if not isinstance(ch["chapter_title"], str) or not ch["chapter_title"].strip():
            errors.append(f"{name}[{ch_key}]: chapter_title must be non-empty string")
        if not isinstance(ch["files"], list) or not ch["files"]:
            errors.append(f"{name}[{ch_key}]: files must be non-empty list")
        else:
            for i, f in enumerate(ch["files"]):
                if not isinstance(f, str) or not f.strip():
                    errors.append(f"{name}[{ch_key}].files[{i}]: must be non-empty string")
        if not isinstance(ch["research_prompt"], str) or len(ch["research_prompt"]) < 50:
            errors.append(f"{name}[{ch_key}]: research_prompt must be string of >=50 chars")

    # Sequential numbering check — only when keys start at chapter 1 (oracle convention).
    if seen_numbers:
        nums_sorted = sorted(seen_numbers.keys())
        if nums_sorted[0] == 1:
            max_n = nums_sorted[-1]
            gap = sorted(set(range(1, max_n + 1)) - set(seen_numbers.keys()))
            if gap:
                errors.append(f"{name}: chapter number gap — missing {gap}")

    return errors


def validate_project_prompts(data: Any, *, name: str = "project_prompts") -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return [f"{name}: top-level must be an object"]
    if "agents" not in data or "tasks" not in data:
        errors.append(f"{name}: missing top-level 'agents' or 'tasks'")
        return errors

    agents = data["agents"]
    if not isinstance(agents, dict):
        errors.append(f"{name}.agents: must be object")
    else:
        missing = PROMPT_REQUIRED_AGENTS - set(agents.keys())
        if missing:
            errors.append(f"{name}.agents: missing agent(s) {sorted(missing)}")
        for agent_name, agent in agents.items():
            if not isinstance(agent, dict):
                errors.append(f"{name}.agents.{agent_name}: must be object")
                continue
            missing_fields = PROMPT_AGENT_FIELDS - set(agent.keys())
            if missing_fields:
                errors.append(f"{name}.agents.{agent_name}: missing field(s) {sorted(missing_fields)}")

    tasks = data["tasks"]
    if not isinstance(tasks, dict):
        errors.append(f"{name}.tasks: must be object")
    else:
        missing = PROMPT_REQUIRED_TASKS - set(tasks.keys())
        if missing:
            errors.append(f"{name}.tasks: missing task(s) {sorted(missing)}")
        for task_name, task in tasks.items():
            if not isinstance(task, dict):
                errors.append(f"{name}.tasks.{task_name}: must be object")
                continue
            missing_fields = PROMPT_TASK_FIELDS - set(task.keys())
            if missing_fields:
                errors.append(f"{name}.tasks.{task_name}: missing field(s) {sorted(missing_fields)}")
                continue
            desc = task.get("description", "")
            if not isinstance(desc, str):
                errors.append(f"{name}.tasks.{task_name}.description: must be string")
                continue
            placeholders = set(re.findall(r"\{(\w+)\}", desc))
            unknown = placeholders - ALLOWED_PLACEHOLDERS
            if unknown:
                errors.append(
                    f"{name}.tasks.{task_name}.description: unknown placeholders "
                    f"{sorted(unknown)} (allowed: {sorted(ALLOWED_PLACEHOLDERS)})"
                )

    return errors
