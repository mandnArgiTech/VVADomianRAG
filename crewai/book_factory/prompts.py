"""Load and format project_prompts.json (agent personas and task templates)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .exceptions import BookFactoryConfigError, BookFactoryIOError


@dataclass(frozen=True)
class AgentPrompts:
    role: str
    goal: str
    backstory: str


@dataclass(frozen=True)
class TaskPromptTemplate:
    description: str
    expected_output: str


@dataclass(frozen=True)
class ProjectPrompts:
    algorithm_researcher: AgentPrompts
    technical_author: AgentPrompts
    research: TaskPromptTemplate
    write_math: TaskPromptTemplate
    write_code: TaskPromptTemplate
    assemble: TaskPromptTemplate


def validate_research_template(pp: ProjectPrompts) -> None:
    """Ensure the research task can splice ledger text without passing it through str.format."""
    rdesc = pp.research.description
    if "{research_prompt}" not in rdesc:
        raise BookFactoryConfigError(
            'project_prompts.json tasks.research.description must contain the literal '
            "substring {research_prompt} exactly once so ledger text is not interpreted as "
            "format placeholders."
        )
    head, tail = rdesc.split("{research_prompt}", 1)
    if "{research_prompt}" in tail:
        raise BookFactoryConfigError(
            "project_prompts.json tasks.research.description: use {research_prompt} at most once."
        )


def format_prompt_template(where: str, template: str, **kwargs: str) -> str:
    try:
        return template.format(**kwargs)
    except KeyError as exc:
        key = exc.args[0] if exc.args else "?"
        raise BookFactoryConfigError(
            f"project_prompts.json template {where!r}: placeholder {key!r} was not supplied at runtime."
        ) from exc
    except ValueError as exc:
        raise BookFactoryConfigError(
            f"project_prompts.json template {where!r}: invalid format string ({exc})."
        ) from exc


def load_project_prompts(prompts_json: Path) -> ProjectPrompts:
    label = str(prompts_json)
    if not prompts_json.is_file():
        raise BookFactoryConfigError(f"Project prompts file not found: {prompts_json}")

    try:
        with prompts_json.open(encoding="utf-8") as f:
            raw: Any = json.load(f)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BookFactoryIOError(f"Cannot load project prompts {prompts_json}: {exc}") from exc

    if not isinstance(raw, dict):
        raise BookFactoryConfigError(f"{label}: root must be a JSON object.")

    def req_str(obj: dict[str, Any], dotted: str, key: str) -> str:
        v = obj.get(key)
        if not isinstance(v, str) or not v.strip():
            raise BookFactoryConfigError(f"{label}: at {dotted!r}, field {key!r} must be a non-empty string.")
        return v.strip()

    agents_raw = raw.get("agents")
    tasks_raw = raw.get("tasks")
    if not isinstance(agents_raw, dict):
        raise BookFactoryConfigError(f'{label}: top-level "agents" must be a JSON object.')
    if not isinstance(tasks_raw, dict):
        raise BookFactoryConfigError(f'{label}: top-level "tasks" must be a JSON object.')

    def load_agent(name: str) -> AgentPrompts:
        blob = agents_raw.get(name)
        dot = f"agents.{name}"
        if not isinstance(blob, dict):
            raise BookFactoryConfigError(f"{label}: {dot!r} must be a JSON object.")
        return AgentPrompts(
            role=req_str(blob, dot, "role"),
            goal=req_str(blob, dot, "goal"),
            backstory=req_str(blob, dot, "backstory"),
        )

    def load_task(name: str) -> TaskPromptTemplate:
        blob = tasks_raw.get(name)
        dot = f"tasks.{name}"
        if not isinstance(blob, dict):
            raise BookFactoryConfigError(f"{label}: {dot!r} must be a JSON object.")
        return TaskPromptTemplate(
            description=req_str(blob, dot, "description"),
            expected_output=req_str(blob, dot, "expected_output"),
        )

    return ProjectPrompts(
        algorithm_researcher=load_agent("algorithm_researcher"),
        technical_author=load_agent("technical_author"),
        research=load_task("research"),
        write_math=load_task("write_math"),
        write_code=load_task("write_code"),
        assemble=load_task("assemble"),
    )
