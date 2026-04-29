# STORY M8 — Add JSON schema validation for oracle / ledger / project_prompts files

**Branch:** `ngspice_rag`  
**Status:** 🔲 TODO  
**Severity:** 🟡 MEDIUM — preventive; catches future regressions early

---

## Problem

The CrewAI book factory loads three classes of JSON config:

| File | Purpose |
|---|---|
| `chapter_ledger.json` / `oracle_*.json` | Per-chapter metadata: `chapter_title`, `files`, `research_prompt` |
| `project_prompts_*.json` | Agent personas + task templates with `.format()` placeholders |
| `config.yaml` | Path config (already validated by `book_factory/config.py`) |

Today, malformed oracles or prompt files are caught only at runtime when CrewAI fails — leading to confusing tracebacks deep inside agent execution. The bugs we found in Stories M5, M6, M7 (missing `CRITICAL`, missing chapter numbers, bare-filename paths) would all have been caught by a schema validator on first run.

---

## Implementation

### Step 1 — Define the schemas

Create `crewai/book_factory/schemas.py`:

```python
"""JSON Schema validation for oracle / project_prompts / ledger inputs."""
from __future__ import annotations
import re
from typing import Any, Dict, List

# Chapter key pattern: Chapter_NNN_<slug>.md (3-digit zero-padded)
CHAPTER_KEY_RE = re.compile(r"^Chapter_(\d{2,3})_[A-Za-z0-9_]+\.md$")

ORACLE_REQUIRED_FIELDS = {"chapter_title", "files", "research_prompt"}

PROMPT_REQUIRED_AGENTS = {"algorithm_researcher", "technical_author"}
PROMPT_REQUIRED_TASKS = {"research", "write_math", "write_code", "assemble"}
PROMPT_AGENT_FIELDS = {"role", "goal", "backstory"}
PROMPT_TASK_FIELDS = {"description", "expected_output"}

# Placeholders that the pipeline supplies via .format()
ALLOWED_PLACEHOLDERS = {"filenames_str", "research_prompt", "chapter_title"}


class SchemaError(ValueError):
    pass


def validate_oracle(data: Any, *, name: str = "oracle") -> List[str]:
    """Return a list of error strings; empty list means valid."""
    errors: List[str] = []
    if not isinstance(data, dict):
        return [f"{name}: top-level must be an object, got {type(data).__name__}"]
    if not data:
        return [f"{name}: contains zero chapters"]

    seen_numbers: Dict[int, str] = {}
    for ch_key, ch in data.items():
        if not CHAPTER_KEY_RE.match(ch_key):
            errors.append(f"{name}[{ch_key}]: key does not match Chapter_NNN_<slug>.md")
            continue
        num = int(CHAPTER_KEY_RE.match(ch_key).group(1))
        if num in seen_numbers:
            errors.append(f"{name}[{ch_key}]: duplicate chapter number {num} (also in {seen_numbers[num]})")
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

    # Sequential numbering check (informational — produces warnings, not errors)
    if seen_numbers:
        nums = sorted(seen_numbers.keys())
        expected = list(range(1, max(nums) + 1))
        gap = sorted(set(expected) - set(nums))
        if gap:
            errors.append(f"{name}: chapter number gap — missing {gap}")

    return errors


def validate_project_prompts(data: Any, *, name: str = "project_prompts") -> List[str]:
    errors: List[str] = []
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
            # Check .format() placeholders
            desc = task.get("description", "")
            placeholders = set(re.findall(r"\{(\w+)\}", desc))
            unknown = placeholders - ALLOWED_PLACEHOLDERS
            if unknown:
                errors.append(
                    f"{name}.tasks.{task_name}.description: unknown placeholders "
                    f"{sorted(unknown)} (allowed: {sorted(ALLOWED_PLACEHOLDERS)})"
                )

    return errors
```

### Step 2 — Wire into `book_factory/cli.py`

After loading the oracle and project_prompts (but before creating the Crew), call the validators and abort cleanly on errors:

```python
from book_factory.schemas import validate_oracle, validate_project_prompts

def _validate_inputs(oracle: dict, prompts: dict, *, oracle_name: str, prompts_name: str) -> None:
    errors = []
    errors += validate_oracle(oracle, name=oracle_name)
    errors += validate_project_prompts(prompts, name=prompts_name)
    if errors:
        log = logging.getLogger("book_factory")
        log.error("Configuration validation failed (%d issues):", len(errors))
        for e in errors:
            log.error("  %s", e)
        raise SystemExit(2)
```

Call `_validate_inputs(...)` before the chapter iteration loop.

### Step 3 — Standalone validator script

Create `crewai/scripts/validate_configs.py`:

```python
"""Standalone validator — run before commit to catch oracle / prompt regressions."""
from __future__ import annotations
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from book_factory.schemas import validate_oracle, validate_project_prompts

def main() -> int:
    base = Path(__file__).resolve().parent.parent
    targets = {
        "chapter_ledger.json": validate_oracle,
        "oracle_kinematica.json": validate_oracle,
        "oracle_nav2.json": validate_oracle,
        "project_prompts_ngspice.json": validate_project_prompts,
        "project_prompts_kinematica.json": validate_project_prompts,
    }
    fail = 0
    for filename, validator in targets.items():
        path = base / filename
        if not path.exists():
            print(f"  SKIP {filename} (not present)")
            continue
        data = json.loads(path.read_text())
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
```

### Step 4 — Tests

Create `tests/test_book_factory_schemas.py`:

```python
"""Schema tests covering happy-path + each detectable failure mode."""
from __future__ import annotations
import json
from pathlib import Path
import pytest

from crewai.book_factory.schemas import validate_oracle, validate_project_prompts


def test_oracle_valid_minimal():
    data = {
        "Chapter_001_Foo.md": {
            "chapter_title": "Foo",
            "files": ["a/b.cpp"],
            "research_prompt": "x" * 60,
        }
    }
    assert validate_oracle(data) == []


def test_oracle_rejects_bad_key():
    data = {"not_a_chapter_key": {"chapter_title": "x", "files": ["a"], "research_prompt": "y" * 60}}
    errors = validate_oracle(data)
    assert any("does not match" in e for e in errors)


def test_oracle_detects_chapter_gap():
    data = {
        "Chapter_001_A.md": {"chapter_title": "A", "files": ["a"], "research_prompt": "x" * 60},
        "Chapter_003_C.md": {"chapter_title": "C", "files": ["c"], "research_prompt": "z" * 60},
    }
    errors = validate_oracle(data)
    assert any("missing [2]" in e for e in errors)


def test_oracle_detects_duplicate_numbers():
    data = {
        "Chapter_001_A.md": {"chapter_title": "A", "files": ["a"], "research_prompt": "x" * 60},
        "Chapter_001_B.md": {"chapter_title": "B", "files": ["b"], "research_prompt": "y" * 60},
    }
    errors = validate_oracle(data)
    assert any("duplicate" in e for e in errors)


def test_oracle_requires_nonempty_files():
    data = {
        "Chapter_001_A.md": {"chapter_title": "A", "files": [], "research_prompt": "x" * 60}
    }
    errors = validate_oracle(data)
    assert any("non-empty list" in e for e in errors)


def test_prompts_valid_minimal():
    data = {
        "agents": {
            "algorithm_researcher": {"role": "r", "goal": "g", "backstory": "b"},
            "technical_author": {"role": "r", "goal": "g", "backstory": "b"},
        },
        "tasks": {
            "research": {"description": "x {filenames_str} {research_prompt}", "expected_output": "y"},
            "write_math": {"description": "x {chapter_title}", "expected_output": "y"},
            "write_code": {"description": "x {chapter_title}", "expected_output": "y"},
            "assemble": {"description": "x {chapter_title} {filenames_str}", "expected_output": "y"},
        },
    }
    assert validate_project_prompts(data) == []


def test_prompts_rejects_unknown_placeholder():
    data = {
        "agents": {
            "algorithm_researcher": {"role": "r", "goal": "g", "backstory": "b"},
            "technical_author": {"role": "r", "goal": "g", "backstory": "b"},
        },
        "tasks": {
            "research": {"description": "x {nonexistent_var}", "expected_output": "y"},
            "write_math": {"description": "x", "expected_output": "y"},
            "write_code": {"description": "x", "expected_output": "y"},
            "assemble": {"description": "x", "expected_output": "y"},
        },
    }
    errors = validate_project_prompts(data)
    assert any("unknown placeholders" in e for e in errors)


def test_real_files_pass(tmp_path):
    """All 5 shipped JSON configs must validate after Stories M5-M7 land."""
    base = Path("crewai")
    for name in ["chapter_ledger.json", "oracle_kinematica.json", "oracle_nav2.json"]:
        if not (base / name).exists():
            continue
        data = json.loads((base / name).read_text())
        errors = validate_oracle(data, name=name)
        # Allow the gap warning until M7 lands; everything else is a hard fail
        hard = [e for e in errors if "chapter number gap" not in e]
        assert hard == [], f"{name} validation errors: {hard}"
```

### Step 5 — Document

Add to `crewai/README.md`:

```markdown
## Validating configs before commit

Run from repo root:

    python crewai/scripts/validate_configs.py

This catches:
- Malformed chapter keys
- Duplicate or out-of-sequence chapter numbers
- Missing required fields (files, research_prompt, …)
- Empty file lists
- Project-prompt placeholders the pipeline can't supply

The book_factory CLI also runs these validators at startup and aborts
with a clear error before invoking any LLM calls.
```

---

## Acceptance Criteria

- [ ] `crewai/book_factory/schemas.py` exports `validate_oracle()` and `validate_project_prompts()`.
- [ ] `crewai/scripts/validate_configs.py` runs against all 5 shipped JSON files and exits non-zero if any fail.
- [ ] `book_factory/cli.py` calls the validators before chapter iteration; aborts with `SystemExit(2)` on any error.
- [ ] `tests/test_book_factory_schemas.py` covers: valid minimal, bad chapter key, gap detection, duplicate numbers, empty files, valid prompts, unknown placeholder, real-file roundtrip.
- [ ] `pytest tests/test_book_factory_schemas.py` passes.
- [ ] `crewai/README.md` documents the validation step.
- [ ] After Stories M5–M7 land, `python crewai/scripts/validate_configs.py` exits 0 against all 5 files.
- [ ] Committed with message `feat(crewai): add JSON schema validation for oracle / project_prompts inputs`.
