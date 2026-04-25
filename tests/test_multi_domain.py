"""STORY G: multi-domain prompts, concept registry, and collection domain filter."""

from __future__ import annotations

import json
from pathlib import Path

import ingest as ing
import mcp_server as mcp
import query as q
import util.search_primitives as sp


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _prompts_dir() -> Path:
    return _repo_root() / "system_prompts"


def test_md01_default_system_prompt_is_generic():
    assert q.DEFAULT_SYSTEM_PROMPT == q._GENERIC_SYSTEM_PROMPT


def test_md02_effective_prompt_code_majority_without_domain_is_generic():
    hits = [
        q.SearchHit("a", None, "code", {}, "c1"),
        q.SearchHit("b", None, "code", {}, "c1"),
        q.SearchHit("c", None, "code", {}, "c1"),
        q.SearchHit("d", None, "rally", {}, "c1"),
    ]
    sp = q._effective_system_prompt(hits, "auto", None, domain="")
    assert sp == q._GENERIC_SYSTEM_PROMPT


def test_md03_domain_spice_loads_spice_engineer():
    text = q._load_system_prompt("spice", _prompts_dir())
    assert "SPICE kernel engineer" in text or "spice" in text.lower()


def test_md04_domain_kinematica_loads_kinematica_engineer():
    text = q._load_system_prompt("kinematica", _prompts_dir())
    assert "ArduPilot" in text or "ArduRover" in text


def test_md05_domain_mujoco_loads_mujoco_engineer():
    text = q._load_system_prompt("mujoco", _prompts_dir())
    assert "MuJoCo" in text


def test_md06_domain_nav2_loads_nav2_engineer():
    text = q._load_system_prompt("nav2", _prompts_dir())
    assert "Nav2" in text or "ROS 2" in text


def test_md07_domain_dart_loads_dart_engineer():
    text = q._load_system_prompt("dart", _prompts_dir())
    assert "DART" in text


def test_md08_domain_filter_dart_matches_dart_code_only():
    names = ["dart_code", "standard_code"]
    assert q._domain_filter(names, "dart") == ["dart_code"]


def test_md09_domain_filter_art_does_not_match_dart_code():
    assert q._domain_filter(["dart_code"], "art") == []


def test_md10_domain_filter_nav_prefix_does_not_match_nav2():
    assert q._domain_filter(["nav2_code"], "nav") == []
    assert q._domain_filter(["nav2_code"], "nav2") == ["nav2_code"]


def test_md11_domain_filter_empty_returns_all():
    names = ["a_code", "b_domain"]
    assert q._domain_filter(names, "") == names
    assert q._domain_filter(names, "general") == names


def test_md12_concept_registry_has_all_five_domains():
    path = _repo_root() / "concept_registry.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    for dom in ("spice", "kinematica", "mujoco", "nav2", "dart"):
        assert dom in data
        assert isinstance(data[dom], dict) and len(data[dom]) >= 1


def test_md13_kinematica_concepts_tag_ekf():
    path = _repo_root() / "concept_registry.json"
    reg = ing.load_concept_registry(path)
    out = ing.extract_concepts("The EKF innovations look noisy.", "kinematica", reg)
    assert "extended_kalman_filter" in out


def test_md14_mujoco_concepts_tag_mjmodel():
    path = _repo_root() / "concept_registry.json"
    reg = ing.load_concept_registry(path)
    out = ing.extract_concepts("We patch mjModel fields here.", "mujoco", reg)
    assert "mujoco_model_struct" in out


def test_md15_nav2_concepts_tag_costmap():
    path = _repo_root() / "concept_registry.json"
    reg = ing.load_concept_registry(path)
    out = ing.extract_concepts("Tune the costmap inflation.", "nav2", reg)
    assert "costmap_2d" in out


def test_md16_dart_concepts_tag_skeleton():
    path = _repo_root() / "concept_registry.json"
    reg = ing.load_concept_registry(path)
    out = ing.extract_concepts("Skeleton joint limits in DART.", "dart", reg)
    assert "dart_skeleton" in out


def test_md17_all_five_engineer_prompt_files_exist():
    sdir = _prompts_dir()
    for name in ("spice", "kinematica", "mujoco", "nav2", "dart"):
        assert (sdir / f"{name}_engineer.md").is_file()


def test_md18_empty_domain_system_prompt_returns_empty():
    assert q._load_system_prompt("", _prompts_dir()) == ""


def test_md19_studio_concept_registry_matches_root_for_story_domains():
    root = json.loads((_repo_root() / "concept_registry.json").read_text(encoding="utf-8"))
    studio = json.loads(
        (_repo_root() / "Studio-Portable-RAG" / "concept_registry.json").read_text(encoding="utf-8")
    )
    for dom in ("spice", "kinematica", "mujoco", "nav2", "dart"):
        assert root[dom] == studio[dom]


def test_md20_domain_filter_unified_in_search_primitives():
    """query and mcp re-export the same ``domain_filter`` (STORY M3); behavior matches md08–md11."""
    assert q._domain_filter is mcp._domain_filter is sp.domain_filter
    names = ["dart_code", "standard_code"]
    assert q._domain_filter(names, "dart") == mcp._domain_filter(names, "dart") == ["dart_code"]
    assert q._domain_filter(["dart_code"], "art") == []
    assert q._domain_filter(["nav2_code"], "nav") == []
    assert q._domain_filter(["nav2_code"], "nav2") == ["nav2_code"]
    all_names = ["a_code", "b_domain"]
    assert q._domain_filter(all_names, "") == q._domain_filter(all_names, "general") == all_names
