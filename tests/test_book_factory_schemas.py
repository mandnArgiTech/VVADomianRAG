"""Schema tests covering happy-path + each detectable failure mode."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_CREWAI = Path(__file__).resolve().parents[1] / "crewai"
if str(_CREWAI) not in sys.path:
    sys.path.insert(0, str(_CREWAI))

from book_factory.schemas import validate_oracle, validate_project_prompts  # noqa: E402


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
    data = {"Chapter_001_A.md": {"chapter_title": "A", "files": [], "research_prompt": "x" * 60}}
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


def test_real_files_pass():
    """Shipped JSON configs must validate (oracle gaps allowed only as non-hard per legacy test)."""
    base = Path(__file__).resolve().parents[1] / "crewai"
    for name in ["chapter_ledger.json", "oracle_kinematica.json", "oracle_nav2.json"]:
        path = base / name
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        errors = validate_oracle(data, name=name)
        hard = [e for e in errors if "chapter number gap" not in e]
        assert hard == [], f"{name} validation errors: {hard}"
