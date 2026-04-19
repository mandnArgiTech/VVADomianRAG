"""STORY D: Gemma default chat model, system prompts, Ollama options, model fallback."""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from unittest.mock import patch


def test_gm01_default_chat_llm_constant(monkeypatch):
    monkeypatch.delenv("RAG_LLM_MODEL", raising=False)
    import query

    assert query.DEFAULT_CHAT_LLM == "gemma3:27b"
    ns = query.parse_args(["-i"])
    assert (ns.llm_model or "").strip() == ""
    st = query.SessionState(ns)
    assert st.llm_model == "gemma3:27b"


def test_gm02_gui_default_dashboard_llm(monkeypatch):
    monkeypatch.delenv("RAG_LLM_MODEL", raising=False)
    import gui_backend

    importlib.reload(gui_backend)
    assert gui_backend.DEFAULT_DASHBOARD_LLM == "gemma3:27b"


def test_gm03_rag_llm_model_env_overrides(monkeypatch):
    monkeypatch.setenv("RAG_LLM_MODEL", "qwen2.5-coder:32b")
    import query

    assert query.default_chat_llm_from_env() == "qwen2.5-coder:32b"
    ns = query.parse_args(["-i"])
    st = query.SessionState(ns)
    assert st.llm_model == "qwen2.5-coder:32b"


def test_gm04_load_system_prompt_spice(tmp_path: Path):
    import query

    sdir = tmp_path / "system_prompts"
    sdir.mkdir()
    (sdir / "spice_engineer.md").write_text("SPICE_DOMAIN_PROMPT\n", encoding="utf-8")
    assert query._load_system_prompt("spice", _prompts_dir=sdir) == "SPICE_DOMAIN_PROMPT"


def test_gm05_load_system_prompt_unknown_no_fallback_file(tmp_path: Path):
    import query

    sdir = tmp_path / "system_prompts"
    sdir.mkdir()
    (sdir / "spice_engineer.md").write_text("only spice\n", encoding="utf-8")
    assert query._load_system_prompt("nonexistent", _prompts_dir=sdir) == ""


def test_gm06_load_system_prompt_falls_back_to_default(tmp_path: Path):
    import query

    sdir = tmp_path / "system_prompts"
    sdir.mkdir()
    (sdir / "default.md").write_text("GENERIC_DEFAULT\n", encoding="utf-8")
    assert query._load_system_prompt("anything", _prompts_dir=sdir) == "GENERIC_DEFAULT"


def test_gm07_ollama_options_gemma():
    import query

    o = query._ollama_options_for_model("gemma3:27b")
    assert o["num_ctx"] == 65536
    assert o["temperature"] == 0.1
    assert o["top_p"] == 0.9
    assert o["repeat_penalty"] == 1.1


def test_gm08_ollama_options_non_gemma():
    import query

    o = query._ollama_options_for_model("qwen2.5-coder:32b")
    assert o["temperature"] == 0.2
    assert o["top_p"] == 0.95
    assert o["num_ctx"] == 32768


def test_gm09_check_model_available_when_present():
    import query

    payload = {"models": [{"name": "gemma3:27b"}, {"name": "nomic-embed-text"}]}
    data = json.dumps(payload).encode()

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return None

        def read(self):
            return data

    with patch.object(query.urllib.request, "urlopen", return_value=_Resp()):
        assert query._check_model_available("gemma3:27b") == "gemma3:27b"


def test_gm10_check_model_available_fallback():
    import query

    payload = {"models": [{"name": "llama3:latest"}]}
    data = json.dumps(payload).encode()

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return None

        def read(self):
            return data

    with patch.object(query.urllib.request, "urlopen", return_value=_Resp()):
        assert query._check_model_available("gemma3:27b") == "llama3:latest"


def test_gm11_spice_engineer_file_size_reasonable():
    root = Path(__file__).resolve().parents[1]
    p = root / "system_prompts" / "spice_engineer.md"
    assert p.is_file()
    text = p.read_text(encoding="utf-8")
    assert len(text) // 4 < 2000


def test_gm12_spice_engineer_terminology():
    root = Path(__file__).resolve().parents[1]
    text = (root / "system_prompts" / "spice_engineer.md").read_text(encoding="utf-8")
    for needle in ("Newton-Raphson", "Jacobian", "companion model", "NodalAI"):
        assert needle in text
