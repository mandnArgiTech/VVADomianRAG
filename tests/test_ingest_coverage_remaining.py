"""Targeted tests to raise ingest.py coverage toward the 95% gate."""
from __future__ import annotations

import asyncio
import importlib.util
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import ingest as ing
from ingest_kit.chunking import code_pipeline as code_pipeline_mod
from ingest_kit import treesitter as treesitter_mod


@pytest.fixture
def no_embed_sleep(monkeypatch):
    monkeypatch.setattr(ing.time, "sleep", lambda *_a, **_k: None)


def test_strip_html_with_beautifulsoup():
    try:
        from bs4 import BeautifulSoup  # noqa: F401
    except ImportError:
        pytest.skip("beautifulsoup4 not installed")
    html = "<p>Hello <b>world</b></p>"
    out = ing.strip_html(html)
    assert "Hello" in out and "world" in out


def test_strip_html_regex_when_beautifulsoup_unavailable(monkeypatch):
    monkeypatch.setattr(ing, "BeautifulSoup", None)
    out = ing.strip_html("<p>x</p>")
    assert "x" in out and "<p>" not in out


def test_file_preamble_comment_not_at_file_start():
    src = "int x;\n/* not at start */\n"
    assert ing._file_preamble_block_comment(src) is None


def test_normalize_refcount_stem_empty_after_strip():
    assert ing._normalize_refcount_stem("   ") == ""


def test_regex_code_split_empty_segments_use_generic(tmp_path: Path, monkeypatch):
    """Newline-only body: ^ matches every line start; stripped segments are empty → generic_split."""
    called: list[bool] = []
    orig = code_pipeline_mod.generic_split

    def wrapped(c: str, p: Path, n: int):
        called.append(True)
        return orig(c, p, n)

    monkeypatch.setattr(code_pipeline_mod, "generic_split", wrapped)
    monkeypatch.setitem(ing._REGEX_CODE_PATTERNS, ".py", [r"^"])
    path = tmp_path / "x.py"
    path.write_text("", encoding="utf-8")
    ing.regex_code_split("\n\n\n", path, ".py")
    assert called


def test_regex_spice_split_falls_back_without_block_markers(tmp_path: Path):
    p = tmp_path / "n.cir"
    p.write_text("no subckt markers here\n", encoding="utf-8")
    out = ing.regex_spice_split("no subckt markers here\n", p)
    assert out


def test_regex_spice_split_blocks(tmp_path: Path):
    p = tmp_path / "x.cir"
    body = (
        "Test title\n"
        ".subckt amp in out\nR1 in out 1k\n.ends\n"
        ".model nmos nmos\n+ level=1\n"
    )
    chunks = ing.regex_spice_split(body, p)
    assert len(chunks) >= 2
    assert all(c[1].get("chunk_strategy") == "regex_spice" for c in chunks)


def test_regex_spice_split_oversize_segment_subsplit(tmp_path: Path):
    """Segments over SPICE_MAX_SEGMENT_CHARS are sub-split without truncating to 8000."""
    big = "x" * 60_000
    body = big + "\n.subckt amp in out\nR1 in out 1k\n.ends\n"
    p = tmp_path / "big.cir"
    out = ing.regex_spice_split(body, p)
    assert out
    assert all(len(c[0]) <= 50_000 for c in out)
    assert sum(len(c[0]) for c in out) >= 60_000


def test_ts_c_cpp_zero_chunks_routes_regex_before_language_split(monkeypatch, tmp_path: Path):
    p = tmp_path / "fallback.c"
    p.write_text("void f(void) {}\n", encoding="utf-8")
    content = p.read_text(encoding="utf-8")
    monkeypatch.setattr(code_pipeline_mod, "_ts_extract_chunks", lambda *a, **k: [])
    out = ing._ts_extract_chunks_or_language_split_c_cpp(
        p, content, "c", allow_language_split_fallback=True
    )
    assert out
    assert any(m.get("chunk_strategy") == "regex_code" for _, m in out)


def test_regex_code_split_empty_stripped_parts_fallback(tmp_path: Path):
    p = tmp_path / "x.rs"
    # Two `fn` headers with only whitespace between -> stripped middle empty -> raw_parts empty -> generic_split
    content = "fn a() {}\n   \nfn b() {}\n"
    out = ing.regex_code_split(content, p, ".rs")
    assert out


def test_parse_ollama_enrichment_tags_and_rel_as_strings():
    raw = '{"summary": "s", "tags": "a, b", "related_functions": "f1, f2"}'
    out = ing._parse_ollama_enrichment_json(raw)
    assert out is not None
    assert out["llm_tags"] == "a,b"
    assert "f1" in out["llm_relations"]


def test_parse_ollama_enrichment_bad_tag_type():
    raw = '{"summary": "s", "tags": 123, "related_functions": []}'
    out = ing._parse_ollama_enrichment_json(raw)
    assert out is not None
    assert out["llm_tags"] == ""


def test_parse_ollama_enrichment_bad_rel_type():
    raw = '{"summary": "s", "tags": [], "related_functions": 3.14}'
    out = ing._parse_ollama_enrichment_json(raw)
    assert out is not None
    assert out["llm_relations"] == ""


def test_ollama_generate_url_custom_enrich():
    custom = "http://localhost:11434"
    with patch.dict("os.environ", {"ENRICH_OLLAMA_URL": custom}, clear=False):
        assert ing._ollama_generate_url().startswith(custom.rstrip("/"))


def test_ollama_generate_url_host_with_scheme():
    with patch.dict("os.environ", {"OLLAMA_HOST": "https://ollama:443", "ENRICH_OLLAMA_URL": ""}, clear=False):
        u = ing._ollama_generate_url()
        assert u.startswith("https://ollama:443")
        assert u.endswith("/api/generate")


def test_ollama_embed_url_with_scheme():
    with patch.dict("os.environ", {"OLLAMA_HOST": "http://127.0.0.1:11434"}, clear=False):
        assert ing._ollama_embed_url() == "http://127.0.0.1:11434/api/embed"


def test_generate_llm_metadata_http_error(monkeypatch):
    err = ing.urllib.error.HTTPError("url", 500, "err", hdrs={}, fp=None)

    def _open(*a, **k):
        raise err

    monkeypatch.setattr(ing.urllib.request, "urlopen", _open)
    out = ing._generate_llm_metadata("x", "n", "m", timeout_sec=1.0)
    assert out["llm_summary"] == ""


def test_generate_llm_metadata_missing_response_field(monkeypatch):
    body = json.dumps({}).encode("utf-8")

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def read(self):
            return body

    monkeypatch.setattr(ing.urllib.request, "urlopen", lambda *a, **k: _Resp())
    out = ing._generate_llm_metadata("x", "n", "m", timeout_sec=1.0)
    assert out["llm_summary"] == ""


def test_http_embed_documents_batch_embeddings_key(monkeypatch):
    payload = json.dumps({"embeddings": [[0.1, 0.2], [0.3, 0.4]]}).encode()

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def read(self):
            return payload

    monkeypatch.setattr(ing.urllib.request, "urlopen", lambda *a, **k: _Resp())
    out = ing.http_embed_documents_batch("m", ["a", "b"], timeout=5.0)
    assert len(out) == 2


def test_http_embed_documents_batch_single_embedding_key(monkeypatch):
    payload = json.dumps({"embedding": [0.5, 0.6]}).encode()

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def read(self):
            return payload

    monkeypatch.setattr(ing.urllib.request, "urlopen", lambda *a, **k: _Resp())
    out = ing.http_embed_documents_batch("m", ["a"], timeout=5.0)
    assert len(out) == 1


def test_http_embed_documents_batch_http_error(monkeypatch):
    err = ing.urllib.error.HTTPError("url", 502, "bad", hdrs={}, fp=None)
    err.fp = None

    def _open(*a, **k):
        raise err

    monkeypatch.setattr(ing.urllib.request, "urlopen", _open)
    with pytest.raises(RuntimeError, match="Ollama embed HTTP"):
        ing.http_embed_documents_batch("m", ["x"], timeout=5.0)


def test_embed_with_retry_serialize_uses_lock(monkeypatch, no_embed_sleep):
    monkeypatch.setenv("EMBED_SERIALIZE", "1")
    emb = MagicMock()
    emb.embed_documents = MagicMock(return_value=[[0.1]])
    out = ing.embed_with_retry(emb, ["a"])
    assert out == [[0.1]]
    emb.embed_documents.assert_called()


def test_embed_with_retry_http_serialize_uses_lock(monkeypatch, no_embed_sleep):
    monkeypatch.setenv("EMBED_SERIALIZE", "1")
    monkeypatch.setattr(
        ing,
        "http_embed_documents_batch",
        lambda model, texts, timeout=300.0: [[0.2] for _ in texts],
    )
    out = ing.embed_with_retry_http("m", ["a", "b"])
    assert out is not None and len(out) == 2


def test_resolve_embed_settings_vram_and_ram_branches(monkeypatch):
    monkeypatch.delenv("EMBED_BATCH_SIZE", raising=False)
    monkeypatch.delenv("EMBED_CONCURRENCY", raising=False)
    monkeypatch.setenv("EMBED_WORKERS", "2")
    monkeypatch.setattr(ing, "_nvidia_total_vram_mb", lambda: 13000)
    monkeypatch.setattr(ing, "_host_total_ram_mb", lambda: 65536)
    b, w, c = ing.resolve_embed_ingest_settings()
    assert b >= 1 and w >= 1 and c >= 1


def test_resolve_embed_settings_low_ram(monkeypatch):
    monkeypatch.setattr(ing, "_nvidia_total_vram_mb", lambda: None)
    monkeypatch.setattr(ing, "_host_total_ram_mb", lambda: 2048)
    monkeypatch.setenv("EMBED_WORKERS", "2")
    b, w, c = ing.resolve_embed_ingest_settings()
    assert b <= 12


def test_git_run_git_missing(monkeypatch):
    def boom(*a, **k):
        raise FileNotFoundError()

    monkeypatch.setattr(ing.subprocess, "run", boom)
    code, out, err = ing._git_run(Path("."), "status")
    assert code == 127


def test_git_diff_file_sets_not_a_repo(tmp_path: Path):
    mod, deleted, head = ing.git_diff_file_sets(tmp_path, "HEAD~1")
    assert mod is None and deleted is None and head is None


def test_write_ngspice_gitignore_appends(tmp_path: Path):
    d = tmp_path / "ng"
    d.mkdir()
    ing.write_ngspice_gitignore(d)
    text = (d / ".gitignore").read_text(encoding="utf-8")
    assert "src/frontend/" in text
    ing.write_ngspice_gitignore(d)
    text2 = (d / ".gitignore").read_text(encoding="utf-8")
    assert text2.count("src/frontend/") == text.count("src/frontend/")


def test_main_write_ngspice_gitignore_only(tmp_path: Path, monkeypatch):
    d = tmp_path / "src"
    d.mkdir()
    monkeypatch.chdir(tmp_path)
    rc = ing.main(["--write-ngspice-gitignore", "--source", str(d)])
    assert rc == 0
    assert (d / ".gitignore").exists()


def test_choose_strategy_spice_ext(tmp_path: Path):
    p = tmp_path / "n.cir"
    p.write_text(".title x\n", encoding="utf-8")
    st, fn, lim, _ = ing.choose_strategy_for_path(p, "code", allow_language_split_fallback=False)
    assert st == "code"
    pieces = fn(p, p.read_text(encoding="utf-8"))
    assert pieces and pieces[0][1].get("chunk_strategy") == "regex_spice"


def test_iter_files_respects_nested_gitignore(tmp_path: Path, monkeypatch):
    if ing.pathspec is None:
        pytest.skip("pathspec not installed")
    monkeypatch.setenv("RESPECT_GITIGNORE", "1")
    root = tmp_path / "r"
    root.mkdir()
    (root / ".gitignore").write_text("*.log\n", encoding="utf-8")
    (root / "keep.c").write_text("//ok\n", encoding="utf-8")
    (root / "skip.log").write_text("x\n", encoding="utf-8")
    paths = ing.iter_files(root, None, skip_dirs=set())
    assert any(p.name == "keep.c" for p in paths)
    assert not any(p.name == "skip.log" for p in paths)


@pytest.mark.skipif(ing.aiohttp is None, reason="aiohttp not installed")
def test_run_async_embedding_batches_returns_none_without_network(monkeypatch):
    async def instant_none(*_a, **_k):
        return None

    monkeypatch.setattr(ing, "embed_with_retry_http_async", instant_none)

    async def run():
        batches = [[("id1", "t1", {"s": "x"})]]
        return await ing.run_async_embedding_batches(batches, "m", 1)

    out = asyncio.run(run())
    assert out == [None]


def test_ingest_code_with_async_embed_mock_batches(
    tmp_path: Path, monkeypatch, patch_ollama_embeddings, concept_registry_path
):
    if ing.aiohttp is None:
        pytest.skip("aiohttp not installed")
    monkeypatch.setenv("EMBED_ASYNC", "1")
    monkeypatch.setenv("EMBED_WORKERS", "1")
    monkeypatch.setenv("EMBEDDING_MODEL", "nomic-embed-text")
    patch_ollama_embeddings(dim=768)

    src = tmp_path / "src"
    src.mkdir()
    (src / "tiny.c").write_text("int z;\n", encoding="utf-8")
    db = tmp_path / "vdb"
    p = ing.build_arg_parser()
    args = p.parse_args(
        [
            "--mode",
            "code",
            "--domain",
            "utcov",
            "--source",
            str(src),
            "--db-path",
            str(db),
            "--concept-registry",
            str(concept_registry_path),
            "--allow-language-split-fallback",
            "--force",
        ]
    )

    async def fake_batches(batches, embed_model, concurrency):
        dim = 768
        out = []
        for b in batches:
            ids = [x[0] for x in b]
            texts = [x[1] for x in b]
            metas = [x[2] for x in b]
            out.append((ids, texts, metas, [[0.03 * (i % 5 + 1) for i in range(dim)] for _ in b]))
        return out

    monkeypatch.setattr(ing, "run_async_embedding_batches", fake_batches)
    assert ing.ingest_run(args) == 0


def test_ingest_enrich_metadata_branch(
    tmp_path: Path, monkeypatch, patch_ollama_embeddings, concept_registry_path
):
    monkeypatch.setenv("EMBED_ASYNC", "0")
    monkeypatch.setenv("EMBED_HTTP", "0")
    monkeypatch.setenv("EMBED_WORKERS", "1")
    monkeypatch.setenv("EMBEDDING_MODEL", "nomic-embed-text")
    patch_ollama_embeddings(dim=768)
    monkeypatch.setattr(
        ing,
        "_generate_llm_metadata",
        lambda *a, **k: {
            "llm_summary": "s",
            "llm_tags": "t",
            "llm_relations": "r",
            "llm_physics_model": "",
        },
    )

    src = tmp_path / "src"
    src.mkdir()
    (src / "a.c").write_text("void f() {}\n", encoding="utf-8")
    db = tmp_path / "vdb"
    p = ing.build_arg_parser()
    args = p.parse_args(
        [
            "--mode",
            "code",
            "--domain",
            "utenc",
            "--source",
            str(src),
            "--db-path",
            str(db),
            "--concept-registry",
            str(concept_registry_path),
            "--allow-language-split-fallback",
            "--enrich-metadata",
            "--enrich-model",
            "dummy",
            "--force",
        ]
    )
    assert ing.ingest_run(args) == 0


def _have_tree_sitter_c() -> bool:
    return all(importlib.util.find_spec(x) is not None for x in ("tree_sitter", "tree_sitter_c"))


@pytest.mark.skipif(not _have_tree_sitter_c(), reason="tree-sitter C not installed")
def test_ts_c_declaration_and_semantic_types(tmp_path: Path):
    p = tmp_path / "devload.c"
    p.write_text(
        "/* file hdr */\n"
        "void BJTload(void) {\n"
        "  int *px, *py;\n"
        "  SMPmatrix *mna;\n"
        "}\n"
        "void MOSsetup(void) {}\n",
        encoding="utf-8",
    )
    chunks = ing._ts_extract_chunks(p, p.read_text(encoding="utf-8"), "c")
    assert chunks
    types = {c[1].get("chunk_type") for c in chunks}
    assert "device_load_function" in types or "device_setup_function" in types


@pytest.mark.skipif(not _have_tree_sitter_c(), reason="tree-sitter C not installed")
def test_ts_c_preproc_and_core_constant(tmp_path: Path):
    p = tmp_path / "cktdefs.h"
    p.write_text("#define CKT_BASE 1\n", encoding="utf-8")
    chunks = ing._ts_extract_chunks(p, p.read_text(encoding="utf-8"), "c")
    assert any(c[1].get("chunk_type") == "core_constant" for c in chunks)


@pytest.mark.skipif(
    not all(importlib.util.find_spec(x) is not None for x in ("tree_sitter", "tree_sitter_java")),
    reason="tree-sitter Java not installed",
)
def test_ts_java_class_walk(tmp_path: Path):
    p = tmp_path / "Hello.java"
    p.write_text(
        "package x;\npublic class Hello {\n  public void run() { }\n}\n",
        encoding="utf-8",
    )
    chunks = ing._ts_extract_chunks(p, p.read_text(encoding="utf-8"), "java")
    names = [c[1].get("chunk_name") for c in chunks]
    assert any("Hello" in str(n) for n in names)


def test_gitignore_parent_chain_and_relpath():
    assert ing._gitignore_parent_chain_dirs("") == [""]
    assert ing._gitignore_parent_chain_dirs("a/b/c") == ["", "a", "a/b"]
    assert ing._relpath_under_gitignore_dir("", "a/b") == "a/b"
    assert ing._relpath_under_gitignore_dir("a", "a/b") == "b"
    assert ing._relpath_under_gitignore_dir("x", "a/b") == "a/b"


def test_read_gitignore_spec_respect_off(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("RESPECT_GITIGNORE", "0")
    cache: dict = {}
    assert ing._read_gitignore_spec_for_dir(tmp_path, "", cache) is None


def test_path_matches_nested_gitignore_file(tmp_path: Path, monkeypatch):
    if ing.pathspec is None:
        pytest.skip("pathspec not installed")
    monkeypatch.setenv("RESPECT_GITIGNORE", "1")
    root = tmp_path / "gr"
    root.mkdir()
    (root / ".gitignore").write_text("secret.txt\n", encoding="utf-8")
    cache: dict = {}
    assert ing._path_matches_any_nested_gitignore(root, "secret.txt", cache, is_dir=False)


def test_ts_language_split_fallback_with_preamble(tmp_path: Path, monkeypatch):
    p = tmp_path / "x.c"
    p.write_text("/* head */\nint a;\n", encoding="utf-8")

    def no_ts(*a, **k):
        return None

    monkeypatch.setattr(code_pipeline_mod, "_ts_extract_chunks", no_ts)
    monkeypatch.setattr(treesitter_mod, "_ts_parser_for", lambda *a, **k: object())
    out = ing._ts_extract_chunks_or_language_split_c_cpp(
        p, p.read_text(encoding="utf-8"), "c", allow_language_split_fallback=True
    )
    assert out
    assert any(m.get("chunk_type") == "file_preamble" for _, m in out)


def test_ingest_tree_sitter_fallback_error_recorded(
    tmp_path: Path, monkeypatch, patch_ollama_embeddings, concept_registry_path
):
    monkeypatch.setenv("EMBED_ASYNC", "0")
    monkeypatch.setenv("EMBED_HTTP", "0")
    monkeypatch.setenv("EMBED_WORKERS", "1")
    patch_ollama_embeddings(dim=768)

    def boom(*a, **k):
        raise ing.TreeSitterFallbackDisallowedError("no ts")

    monkeypatch.setattr(ing, "choose_strategy_for_path", lambda *a, **k: ("code", boom, 50, None))

    src = tmp_path / "src"
    src.mkdir()
    (src / "weird.c").write_text("x\n", encoding="utf-8")
    db = tmp_path / "vdb"
    p = ing.build_arg_parser()
    args = p.parse_args(
        [
            "--mode",
            "code",
            "--domain",
            "utbf",
            "--source",
            str(src),
            "--db-path",
            str(db),
            "--concept-registry",
            str(concept_registry_path),
            "--force",
        ]
    )
    assert ing.ingest_run(args) == 1


@pytest.mark.skipif(ing.aiohttp is None, reason="aiohttp not installed")
def test_run_async_embedding_batches_happy_path(monkeypatch):
    class Resp:
        def raise_for_status(self):
            pass

        async def json(self):
            return {"embeddings": [[0.01] * 4, [0.02] * 4]}

    class PostCM:
        async def __aenter__(self):
            return Resp()

        async def __aexit__(self, *a):
            pass

    class Session:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            pass

        def post(self, url, json=None, timeout=None):
            return PostCM()

    class CT:
        def __init__(self, total=None):
            self.total = total

    monkeypatch.setattr(ing.aiohttp, "ClientSession", lambda **kw: Session())
    monkeypatch.setattr(ing.aiohttp, "ClientTimeout", CT)

    async def run():
        batches = [[("i1", "t1", {"s": "x"}), ("i2", "t2", {"s": "y"})]]
        return await ing.run_async_embedding_batches(batches, "m", 2)

    out = asyncio.run(run())
    assert len(out) == 1 and out[0] is not None
    ids, texts, metas, vecs = out[0]  # type: ignore[misc]
    assert len(ids) == 2 and len(vecs) == 2


def test_async_http_embed_batch_unexpected_keys_raises(monkeypatch):
    if ing.aiohttp is None:
        pytest.skip("aiohttp not installed")

    class Resp:
        def raise_for_status(self):
            pass

        async def json(self):
            return {"weird": True}

    class PostCM:
        async def __aenter__(self):
            return Resp()

        async def __aexit__(self, *a):
            pass

    class Sess:
        def post(self, url, json=None, timeout=None):
            return PostCM()

    monkeypatch.setattr(ing.aiohttp, "ClientTimeout", lambda total=None: object())

    async def run():
        with pytest.raises(RuntimeError, match="Unexpected Ollama embed"):
            await ing._async_http_embed_batch(Sess(), "m", ["a"], timeout=5.0)

    asyncio.run(run())


def test_embed_with_retry_http_async_split_branch(monkeypatch):
    if ing.aiohttp is None:
        pytest.skip("aiohttp not installed")
    monkeypatch.setattr(ing, "EMBED_BACKOFF_SEC", 0.0)

    async def flaky(session, model, texts, timeout=300.0):
        if len(texts) > 1:
            raise RuntimeError("split me")
        return [[0.1, 0.2]]

    monkeypatch.setattr(ing, "_async_http_embed_batch", flaky)

    async def run():
        return await ing.embed_with_retry_http_async(None, "m", ["a", "b"], None)

    out = asyncio.run(run())
    assert out is not None and len(out) == 2


def test_ingest_async_run_raises_records_failed(
    monkeypatch, tmp_path, patch_ollama_embeddings, concept_registry_path
):
    if ing.aiohttp is None:
        pytest.skip("aiohttp not installed")
    monkeypatch.setenv("EMBED_ASYNC", "1")
    monkeypatch.setenv("EMBED_WORKERS", "1")
    patch_ollama_embeddings(dim=768)

    src = tmp_path / "src"
    src.mkdir()
    (src / "one.c").write_text("int q;\n", encoding="utf-8")
    db = tmp_path / "vdb"
    p = ing.build_arg_parser()
    args = p.parse_args(
        [
            "--mode",
            "code",
            "--domain",
            "utasyncfail",
            "--source",
            str(src),
            "--db-path",
            str(db),
            "--concept-registry",
            str(concept_registry_path),
            "--allow-language-split-fallback",
            "--force",
        ]
    )

    def boom(coro):
        coro.close()
        raise RuntimeError("async embed boom")

    monkeypatch.setattr(ing.asyncio, "run", boom)
    assert ing.ingest_run(args) == 1


def test_main_write_ngspice_missing_source_errors():
    with pytest.raises(SystemExit):
        ing.main(["--write-ngspice-gitignore"])


def test_main_write_ngspice_bad_path_errors(tmp_path):
    p = tmp_path / "nope.txt"
    p.write_text("x", encoding="utf-8")
    with pytest.raises(SystemExit):
        ing.main(["--write-ngspice-gitignore", "--source", str(p)])


@pytest.mark.skipif(ing.pathspec is None, reason="pathspec not installed")
def test_iter_files_nested_gitignore_excludes_file(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("RESPECT_GITIGNORE", "1")
    root = tmp_path / "repo"
    inner = root / "inner"
    inner.mkdir(parents=True)
    (inner / ".gitignore").write_text("*.secret\n", encoding="utf-8")
    (inner / "keep.c").write_text("// ok\n", encoding="utf-8")
    (inner / "hide.secret").write_text("x", encoding="utf-8")
    paths = ing.iter_files(root, {".c", ".secret"})
    assert (inner / "keep.c") in paths
    assert (inner / "hide.secret") not in paths


def test_gitignore_helpers_paths_and_relpath(tmp_path: Path):
    r = tmp_path.resolve()
    assert ing._gitignore_file_path(r, "") == r / ".gitignore"
    assert ing._gitignore_file_path(r, "a/b") == r / "a" / "b" / ".gitignore"
    assert ing._relpath_under_gitignore_dir("", "foo/bar") == "foo/bar"
    assert ing._relpath_under_gitignore_dir("foo", "foo/bar") == "bar"
    assert ing._relpath_under_gitignore_dir("foo", "other/bar") == "other/bar"
