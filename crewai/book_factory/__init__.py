"""Ngspice book factory: batch CrewAI pipeline from ledger + C sources.

Use ``from book_factory.cli import main`` (or run ``ngspice_book_factory.py``) for the CLI.
This package avoids importing CrewAI until ``cli`` or ``pipeline`` is loaded.
"""

from __future__ import annotations

from .config import BookFactorySettings, parse_yaml_file, resolve_book_factory_settings
from .exceptions import BookFactoryConfigError, BookFactoryError, BookFactoryIOError
from .prompts import AgentPrompts, ProjectPrompts, TaskPromptTemplate

__all__ = [
    "AgentPrompts",
    "BookFactoryConfigError",
    "BookFactoryError",
    "BookFactoryIOError",
    "BookFactorySettings",
    "ProjectPrompts",
    "TaskPromptTemplate",
    "parse_yaml_file",
    "resolve_book_factory_settings",
]
