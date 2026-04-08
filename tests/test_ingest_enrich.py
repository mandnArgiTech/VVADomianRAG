"""Tests for Ollama LLM metadata enrichment (_generate_llm_metadata)."""
from __future__ import annotations

import json
import ingest as ing


def test_parse_ollama_enrichment_json_plain():
    raw = '{"summary": "loads matrix", "tags": ["BJT", "MNA"], "related_functions": ["SPload"]}'
    out = ing._parse_ollama_enrichment_json(raw)
    assert out is not None
    assert out["llm_summary"] == "loads matrix"
    assert out["llm_tags"] == "BJT,MNA"
    assert out["llm_relations"] == "SPload"


def test_parse_ollama_enrichment_json_fenced():
    raw = '```json\n{"summary": "x", "tags": ["a"], "related_functions": ["b"]}\n```'
    out = ing._parse_ollama_enrichment_json(raw)
    assert out is not None
    assert out["llm_summary"] == "x"
    assert out["llm_tags"] == "a"
    assert out["llm_relations"] == "b"


def test_parse_ollama_enrichment_json_invalid():
    assert ing._parse_ollama_enrichment_json("not json") is None


def test_parse_ollama_enrichment_json_tags_truncated_to_three():
    raw = '{"summary": "s", "tags": ["1", "2", "3", "4"], "related_functions": []}'
    out = ing._parse_ollama_enrichment_json(raw)
    assert out["llm_tags"] == "1,2,3"


def test_generate_llm_metadata_success(monkeypatch):
    body = json.dumps(
        {
            "response": (
                '{"summary": "one line", "tags": ["VDMOS"], "related_functions": ["BSIM4load"]}'
            )
        }
    ).encode("utf-8")

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def read(self):
            return body

    monkeypatch.setattr(ing.urllib.request, "urlopen", lambda *a, **k: _Resp())
    out = ing._generate_llm_metadata("int x;", "myfn", "qwen2.5:0.5b", timeout_sec=5.0)
    assert out["llm_summary"] == "one line"
    assert out["llm_tags"] == "VDMOS"
    assert out["llm_relations"] == "BSIM4load"


def test_generate_llm_metadata_fallback_after_bad_json(monkeypatch):
    calls = {"n": 0}

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def read(self):
            calls["n"] += 1
            if calls["n"] < 3:
                return json.dumps({"response": "not valid json {{{"}).encode("utf-8")
            return json.dumps(
                {"response": '{"summary": "ok", "tags": [], "related_functions": []}'}
            ).encode("utf-8")

    monkeypatch.setattr(ing.urllib.request, "urlopen", lambda *a, **k: _Resp())
    out = ing._generate_llm_metadata("c", "f", "m", timeout_sec=5.0)
    assert out["llm_summary"] == "ok"


def test_generate_llm_metadata_http_error_empty(monkeypatch):
    import urllib.error

    def boom(*a, **k):
        raise urllib.error.HTTPError("url", 500, "err", hdrs={}, fp=None)

    monkeypatch.setattr(ing.urllib.request, "urlopen", boom)
    out = ing._generate_llm_metadata("c", "f", "m", timeout_sec=1.0)
    assert out == {"llm_summary": "", "llm_tags": "", "llm_relations": ""}


def test_ollama_generate_url_from_host(monkeypatch):
    monkeypatch.delenv("ENRICH_OLLAMA_URL", raising=False)
    monkeypatch.setenv("OLLAMA_HOST", "127.0.0.1:11434")
    u = ing._ollama_generate_url()
    assert u.endswith("/api/generate")
    assert "11434" in u
