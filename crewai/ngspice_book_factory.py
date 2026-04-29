"""
Ngspice Book Factory — batch CrewAI pipeline.

Iterates ``chapter_ledger.json`` (chapter specs) to read C sources and produce one Markdown chapter
per entry under ``crewai/output/``.  Already-generated chapters are skipped on
re-run so the batch is resumable.

Pipeline per chapter
--------------------
1. **Research** — ``FileReadTool`` reads the C sources; the researcher agent
   extracts mathematics and data-structure mappings.
2. **Write math** — author drafts *Mathematical Formulation / Convergence*.
3. **Write code** — author drafts *C Implementation / Solver Linkage*.
4. **Assemble** — author merges both drafts into a cohesive chapter.

Operational notes
-----------------
- **deepseek-reasoner** can go silent for many minutes; heartbeats confirm the
  process is alive.
- Set ``CREW_FAST=1`` so the researcher uses **deepseek-chat** for quicker
  iteration.
- Edit ``crewai/chapter_ledger.json`` to add or reorder chapters (no Python edit required).
- Edit ``crewai/project_prompts.json`` for agent personas and task templates (path overridable in YAML).
- Defaults and overrides: ``crewai/config.yaml`` (auto-loaded if present), environment variables,
  then CLI (``--config``, ``--log-file``, etc.). See comments in ``crewai/config.yaml``.

Implementation lives in ``crewai/book_factory/``; this file is the CLI entry point.
"""
from __future__ import annotations

from book_factory.cli import main

if __name__ == "__main__":
    main()
