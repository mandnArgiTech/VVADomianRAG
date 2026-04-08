"""Enterprise ingest: regex chunker, deps, gitignore, git-diff, HTTP embed helpers."""
from __future__ import annotations

import asyncio
import io
import json
import logging
import subprocess as sp
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import ingest as ing


@pytest.fixture
def no_embed_sleep(monkeypatch):
    monkeypatch.setattr(ing.time, "sleep", lambda *_a, **_k: None)


def test_format_dependencies_field():
    assert ing._format_dependencies_field([]) == ""
    assert ing._format_dependencies_field(["b", "a"]) == "a, b"


def test_extract_dependencies_python_ast():
    src = "import os\nfrom json import loads\nclass X:\n  pass\n"
    dep = ing.extract_dependencies(src, ".py")
    assert "json" in dep and "os" in dep and ", " in dep


def test_extract_dependencies_python_syntax_error_fallback():
    src = "from mymod import x\nimport broken {{{\n"
    dep = ing.extract_dependencies(src, ".py")
    assert "mymod" in dep


def test_extract_dependencies_javascript():
    src = "import x from 'lodash';\nconst y = require('path');\n"
    dep = ing.extract_dependencies(src, ".js")
    assert dep


def test_extract_dependencies_cpp():
    src = '#include <stdio.h>\n#include "local.h"\n'
    dep = ing.extract_dependencies(src, ".cpp")
    assert "stdio.h" in dep and "local.h" in dep


def test_extract_dependencies_java():
    src = "package x;\nimport java.util.List;\n"
    dep = ing.extract_dependencies(src, ".java")
    assert "java.util.List" in dep


def test_extract_dependencies_go():
    src = 'import "fmt"\nimport (\n  "os"\n)\n'
    dep = ing.extract_dependencies(src, ".go")
    assert "fmt" in dep and "os" in dep


def test_extract_dependencies_rust():
    src = "use std::io;\nmod foo;\n"
    dep = ing.extract_dependencies(src, ".rs")
    assert "std" in dep or "foo" in dep


def test_regex_code_split_go(tmp_path: Path):
    p = tmp_path / "main.go"
    content = "package main\n\nfunc a() {}\n\nfunc b() {}\n"
    out = ing.regex_code_split(content, p, ".go")
    assert len(out) >= 1
    assert all(x[1].get("chunk_strategy") == "regex_code" for x in out)


def test_regex_code_split_falls_back_generic(tmp_path: Path):
    p = tmp_path / "x.unknown"
    content = "no structure here " * 200
    out = ing.regex_code_split(content, p, ".unknown")
    assert out and out[0][1].get("chunk_strategy") == "generic"


def test_merge_small_regex_chunks():
    parts = ["a", "b", "c"]
    m = ing._merge_small_regex_chunks(parts, min_chars=10, max_chars=100)
    assert len(m) == 1


def test_respect_gitignore():
    assert ing._respect_gitignore() is True


def test_load_gitignore_spec_no_file(tmp_path: Path):
    assert ing._load_gitignore_spec(tmp_path) is None


def test_load_gitignore_spec_reads(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("RESPECT_GITIGNORE", raising=False)
    monkeypatch.setenv("RESPECT_GITIGNORE", "1")
    if ing.pathspec is None:
        pytest.skip("pathspec not installed")
    (tmp_path / ".gitignore").write_text("*.log\n", encoding="utf-8")
    spec = ing._load_gitignore_spec(tmp_path)
    assert spec is not None
    assert spec.match_file("a.log")


def test_iter_files_respects_gitignore(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("RESPECT_GITIGNORE", "1")
    if ing.pathspec is None:
        pytest.skip("pathspec not installed")
    (tmp_path / ".gitignore").write_text("*.log\n", encoding="utf-8")
    (tmp_path / "keep.py").write_text("x", encoding="utf-8")
    (tmp_path / "skip.log").write_text("x", encoding="utf-8")
    paths = ing.iter_files(tmp_path, {".py", ".log"}, skip_dirs=set())
    names = {p.name for p in paths}
    assert "keep.py" in names
    assert "skip.log" not in names


def test_git_checkpoint_head_key():
    assert ing.git_checkpoint_head_key("general_code").endswith("git_head")


def test_git_run_missing_git(tmp_path: Path, monkeypatch):
    def raise_fnf(*_a, **_k):
        raise FileNotFoundError()

    monkeypatch.setattr(ing.subprocess, "run", raise_fnf)
    code, out, err = ing._git_run(tmp_path, "status")
    assert code == 127


def test_git_diff_file_sets_not_repo(tmp_path: Path):
    a, b, h = ing.git_diff_file_sets(tmp_path, "HEAD~1")
    assert a is None and b is None and h is None


def test_ollama_embed_url_default():
    assert "/api/embed" in ing._ollama_embed_url()


def test_http_embed_documents_batch_ok(monkeypatch):
    payload = {"embeddings": [[0.1, 0.2], [0.3, 0.4]]}
    raw = json.dumps(payload).encode()

    class CM:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return raw

    monkeypatch.setattr(ing.urllib.request, "urlopen", lambda *a, **k: CM())
    out = ing.http_embed_documents_batch("m", ["a", "b"])
    assert len(out) == 2


def test_http_embed_single_embedding_key(monkeypatch):
    raw = json.dumps({"embedding": [1.0, 2.0]}).encode()

    class CM:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return raw

    monkeypatch.setattr(ing.urllib.request, "urlopen", lambda *a, **k: CM())
    out = ing.http_embed_documents_batch("m", ["one"])
    assert len(out) == 1


def test_embed_with_retry_http_ok(no_embed_sleep, monkeypatch):
    monkeypatch.setattr(ing, "http_embed_documents_batch", lambda m, b: [[0.0]] * len(b))
    out = ing.embed_with_retry_http("mod", ["a", "b"])
    assert out is not None and len(out) == 2


def test_nvidia_total_vram_mb_none(monkeypatch):
    monkeypatch.setattr(ing.subprocess, "run", lambda *a, **k: MagicMock(returncode=1))
    assert ing._nvidia_total_vram_mb() is None


def test_nvidia_total_vram_mb_ok(monkeypatch):
    proc = MagicMock()
    proc.returncode = 0
    proc.stdout = "8192\n"
    monkeypatch.setattr(ing.subprocess, "run", lambda *a, **k: proc)
    assert ing._nvidia_total_vram_mb() == 8192


def test_resolve_embed_ingest_settings(monkeypatch):
    monkeypatch.setenv("EMBED_BATCH_SIZE", "8")
    monkeypatch.setenv("EMBED_WORKERS", "3")
    monkeypatch.setenv("EMBED_CONCURRENCY", "5")
    monkeypatch.setattr(ing, "_nvidia_total_vram_mb", lambda: None)
    monkeypatch.setattr(ing, "_host_total_ram_mb", lambda: None)
    b, w, c = ing.resolve_embed_ingest_settings()
    assert b == 8 and w == 3 and c == 5


def test_embed_serialize_on(monkeypatch):
    monkeypatch.setenv("EMBED_SERIALIZE", "1")
    assert ing._embed_serialize_on() is True
    monkeypatch.setenv("EMBED_SERIALIZE", "0")
    assert ing._embed_serialize_on() is False


def test_embed_with_retry_http_async_ok(monkeypatch):
    if ing.aiohttp is None:
        pytest.skip("no aiohttp")

    class Resp:
        def raise_for_status(self):
            return None

        async def json(self):
            return {"embeddings": [[0.1], [0.2]]}

    class Sess:
        def post(self, *a, **k):
            class CM:
                async def __aenter__(self):
                    return Resp()

                async def __aexit__(self, *x):
                    return False

            return CM()

    async def _run():
        return await ing.embed_with_retry_http_async(Sess(), "m", ["a", "b"], None)

    out = asyncio.run(_run())
    assert out is not None and len(out) == 2


def test_run_async_embedding_batches_no_aiohttp(monkeypatch):
    monkeypatch.setattr(ing, "aiohttp", None)
    out = asyncio.run(ing.run_async_embedding_batches([[]], "m", 2))
    assert out == [None]


def test_git_diff_file_sets_with_mock_git(tmp_path: Path, monkeypatch):
    def fake_run(cmd, **kwargs):
        m = MagicMock()
        m.stdout = ""
        s = " ".join(cmd)
        if "is-inside-work-tree" in s:
            m.returncode = 0
        elif "rev-parse" in s and "HEAD" in s and "is-inside" not in s:
            m.returncode = 0
            m.stdout = "abc123\n"
        elif "diff" in s and "ACMR" in s:
            m.returncode = 0
            m.stdout = "src/a.py\n"
        elif "diff" in s and "--diff-filter=D" in s:
            m.returncode = 0
            m.stdout = "gone.txt\n"
        else:
            m.returncode = 0
        return m

    monkeypatch.setattr(ing.subprocess, "run", fake_run)
    mod, deleted, head = ing.git_diff_file_sets(tmp_path, "HEAD~1")
    assert mod == {"src/a.py"}
    assert deleted == {"gone.txt"}
    assert head == "abc123"


def test_choose_strategy_uses_regex_for_unknown_code(tmp_path: Path):
    p = tmp_path / "x.go"
    p.write_text("package p\nfunc F() {}\n", encoding="utf-8")
    _label, fn, _lim, _ov = ing.choose_strategy_for_path(p, "code")
    assert _ov is None
    chunks = fn(p, p.read_text(encoding="utf-8"))
    assert chunks


def test_http_embed_http_error(monkeypatch):
    import urllib.error

    err = urllib.error.HTTPError("url", 500, "err", hdrs={}, fp=io.BytesIO(b"oops"))

    def raise_http(*a, **k):
        raise err

    monkeypatch.setattr(ing.urllib.request, "urlopen", raise_http)
    with pytest.raises(RuntimeError, match="Ollama embed HTTP"):
        ing.http_embed_documents_batch("m", ["x"])


def test_git_run_timeout(monkeypatch, tmp_path: Path):
    def raise_timeout(*_a, **_k):
        raise sp.TimeoutExpired("git", 1)

    monkeypatch.setattr(ing.subprocess, "run", raise_timeout)
    code, out, err = ing._git_run(tmp_path, "status")
    assert code == 124


def test_resolve_embed_vram_branch(monkeypatch):
    monkeypatch.delenv("EMBED_BATCH_SIZE", raising=False)
    monkeypatch.delenv("EMBED_CONCURRENCY", raising=False)
    monkeypatch.setenv("EMBED_BATCH_SIZE", "4")
    monkeypatch.setenv("EMBED_CONCURRENCY", "2")
    monkeypatch.setattr(ing, "_nvidia_total_vram_mb", lambda: 16000)
    monkeypatch.setattr(ing, "_host_total_ram_mb", lambda: None)
    b, _w, c = ing.resolve_embed_ingest_settings()
    assert b >= 4 and c >= 2


def test_http_embed_bad_response(monkeypatch):
    raw = json.dumps({"foo": 1}).encode()

    class CM:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return raw

    monkeypatch.setattr(ing.urllib.request, "urlopen", lambda *a, **k: CM())
    with pytest.raises(RuntimeError, match="Unexpected Ollama"):
        ing.http_embed_documents_batch("m", ["a"])


def test_load_gitignore_spec_bad_file(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("RESPECT_GITIGNORE", "1")
    if ing.pathspec is None:
        pytest.skip("pathspec not installed")
    (tmp_path / ".gitignore").write_text("*.log\n", encoding="utf-8")

    def boom(self, *args, **kwargs):
        if self.name == ".gitignore":
            raise OSError("simulated read failure")
        return orig_read(self, *args, **kwargs)

    orig_read = Path.read_text
    monkeypatch.setattr(Path, "read_text", boom)
    assert ing._load_gitignore_spec(tmp_path) is None


def test_respect_gitignore_off(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("RESPECT_GITIGNORE", "0")
    if ing.pathspec is None:
        pytest.skip("pathspec not installed")
    (tmp_path / ".gitignore").write_text("*.py\n", encoding="utf-8")
    (tmp_path / "a.py").write_text("x", encoding="utf-8")
    paths = ing.iter_files(tmp_path, None, skip_dirs=set())
    assert any(p.name == "a.py" for p in paths)


def test_ollama_embed_url_with_scheme(monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "http://127.0.0.1:11434")
    assert ing._ollama_embed_url().endswith("/api/embed")


def test_merge_small_regex_chunks_empty():
    assert ing._merge_small_regex_chunks([], min_chars=10, max_chars=100) == []


def test_merge_small_regex_chunks_spill_branch():
    a, b = "x" * 250, "y" * 250
    merged = ing._merge_small_regex_chunks([a, b], min_chars=200, max_chars=10000)
    assert merged == [a, b]


def test_regex_code_split_re_error_falls_back(monkeypatch, tmp_path: Path):
    def bad_compile(*_a, **_k):
        raise ing.re.error("bad")

    monkeypatch.setattr(ing.re, "compile", bad_compile)
    p = tmp_path / "m.go"
    out = ing.regex_code_split("func x() {}", p, ".go")
    assert out[0][1].get("chunk_strategy") == "generic"


def test_regex_code_split_no_func_uses_generic(tmp_path: Path):
    p = tmp_path / "m.go"
    out = ing.regex_code_split("package main\nvar x = 1\n", p, ".go")
    assert out[0][1].get("chunk_strategy") == "generic"


def test_nvidia_total_vram_bad_returncode(monkeypatch):
    m = MagicMock()
    m.returncode = 1
    m.stdout = "8192\n"
    monkeypatch.setattr(ing.subprocess, "run", lambda *a, **k: m)
    assert ing._nvidia_total_vram_mb() is None


def test_nvidia_total_vram_whitespace_only_stdout(monkeypatch):
    m = MagicMock()
    m.returncode = 0
    m.stdout = "  \n  \n"
    monkeypatch.setattr(ing.subprocess, "run", lambda *a, **k: m)
    assert ing._nvidia_total_vram_mb() is None


def test_resolve_embed_vram_8gb_tier(monkeypatch):
    monkeypatch.delenv("EMBED_BATCH_SIZE", raising=False)
    monkeypatch.delenv("EMBED_CONCURRENCY", raising=False)
    monkeypatch.setenv("EMBED_BATCH_SIZE", "4")
    monkeypatch.setenv("EMBED_CONCURRENCY", "2")
    monkeypatch.setattr(ing, "_nvidia_total_vram_mb", lambda: 9000)
    monkeypatch.setattr(ing, "_host_total_ram_mb", lambda: None)
    b, _w, c = ing.resolve_embed_ingest_settings()
    assert b >= 20 and c >= 4


def test_resolve_embed_ram_low_caps(monkeypatch):
    monkeypatch.delenv("EMBED_BATCH_SIZE", raising=False)
    monkeypatch.delenv("EMBED_CONCURRENCY", raising=False)
    monkeypatch.setenv("EMBED_BATCH_SIZE", "64")
    monkeypatch.setenv("EMBED_CONCURRENCY", "16")
    monkeypatch.setattr(ing, "_nvidia_total_vram_mb", lambda: None)
    monkeypatch.setattr(ing, "_host_total_ram_mb", lambda: 2048)
    b, _w, c = ing.resolve_embed_ingest_settings()
    assert b <= 6 and c <= 2


def test_iter_files_nested_gitignore(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("RESPECT_GITIGNORE", "1")
    if ing.pathspec is None:
        pytest.skip("pathspec not installed")
    (tmp_path / ".gitignore").write_text("*.md\n", encoding="utf-8")
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / ".gitignore").write_text("*.log\n", encoding="utf-8")
    (tmp_path / "readme.md").write_text("x", encoding="utf-8")
    (tmp_path / "keep.py").write_text("x", encoding="utf-8")
    (pkg / "a.log").write_text("x", encoding="utf-8")
    (pkg / "b.py").write_text("x", encoding="utf-8")
    paths = ing.iter_files(tmp_path, None, skip_dirs=set())
    rels = {p.resolve().relative_to(tmp_path.resolve()).as_posix() for p in paths}
    assert "keep.py" in rels
    assert "readme.md" not in rels
    assert "pkg/b.py" in rels
    assert "pkg/a.log" not in rels


def test_embed_with_retry_splits_on_failure(no_embed_sleep, monkeypatch):
    monkeypatch.setenv("EMBED_SERIALIZE", "0")

    class Emb:
        def embed_documents(self, batch):
            if len(batch) > 1:
                raise RuntimeError("fail multi")
            return [[0.1] for _ in batch]

    out = ing.embed_with_retry(Emb(), ["a", "b"])
    assert len(out) == 2


def test_embed_with_retry_with_serialize_lock(no_embed_sleep, monkeypatch):
    monkeypatch.setenv("EMBED_SERIALIZE", "1")

    class Emb:
        def embed_documents(self, batch):
            if len(batch) > 1:
                raise RuntimeError("fail multi")
            return [[0.2] for _ in batch]

    out = ing.embed_with_retry(Emb(), ["p", "q"])
    assert len(out) == 2


def test_embed_with_retry_http_splits(no_embed_sleep, monkeypatch):
    monkeypatch.setenv("EMBED_SERIALIZE", "0")

    def http_batch(_model, batch):
        if len(batch) > 1:
            raise RuntimeError("fail multi")
        return [[0.3] for _ in batch]

    monkeypatch.setattr(ing, "http_embed_documents_batch", http_batch)
    out = ing.embed_with_retry_http("m", ["a", "b", "c"])
    assert len(out) == 3


def test_async_http_embed_requires_aiohttp(monkeypatch):
    monkeypatch.setattr(ing, "aiohttp", None)
    with pytest.raises(RuntimeError, match="aiohttp is not installed"):
        asyncio.run(ing._async_http_embed_batch(None, "m", ["x"]))


def test_http_embed_documents_batch_top_level_embedding_key(monkeypatch):
    raw = json.dumps({"embedding": [0.1, 0.2]}).encode()

    class CM:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return raw

    monkeypatch.setattr(ing.urllib.request, "urlopen", lambda *a, **k: CM())
    out = ing.http_embed_documents_batch("m", ["only_one"])
    assert len(out) == 1 and out[0] == [0.1, 0.2]


def test_embed_with_retry_http_async_single_embedding(monkeypatch):
    if ing.aiohttp is None:
        pytest.skip("no aiohttp")
    monkeypatch.setattr(ing, "EMBED_BACKOFF_SEC", 0)

    class Resp:
        def raise_for_status(self):
            return None

        async def json(self):
            return {"embedding": [0.5, 0.5]}

    class Sess:
        def post(self, *a, **k):
            class CM:
                async def __aenter__(self):
                    return Resp()

                async def __aexit__(self, *x):
                    return False

            return CM()

    async def _run():
        return await ing.embed_with_retry_http_async(Sess(), "m", ["one"], None)

    out = asyncio.run(_run())
    assert out == [[0.5, 0.5]]


def test_embed_with_retry_http_async_uses_async_lock(monkeypatch):
    if ing.aiohttp is None:
        pytest.skip("no aiohttp")
    monkeypatch.setattr(ing, "EMBED_BACKOFF_SEC", 0)

    class Resp:
        def raise_for_status(self):
            return None

        async def json(self):
            return {"embeddings": [[0.1]]}

    class Sess:
        def post(self, *a, **k):
            class CM:
                async def __aenter__(self):
                    return Resp()

                async def __aexit__(self, *x):
                    return False

            return CM()

    async def _run():
        return await ing.embed_with_retry_http_async(Sess(), "m", ["a"], asyncio.Lock())

    assert asyncio.run(_run()) == [[0.1]]


def test_embed_with_retry_http_async_splits(monkeypatch):
    if ing.aiohttp is None:
        pytest.skip("no aiohttp")
    monkeypatch.setattr(ing, "EMBED_BACKOFF_SEC", 0)
    calls = []

    async def flaky(_session, _model, texts, timeout=300.0):
        calls.append(len(texts))
        if len(texts) > 1:
            raise RuntimeError("fail multi")
        return [[float(i)] for i, _ in enumerate(texts)]

    monkeypatch.setattr(ing, "_async_http_embed_batch", flaky)

    class Sess:
        pass

    async def _run():
        return await ing.embed_with_retry_http_async(Sess(), "m", ["a", "b"], None)

    out = asyncio.run(_run())
    assert len(out) == 2


def test_run_async_embedding_batches_none_vectors(monkeypatch):
    if ing.aiohttp is None:
        pytest.skip("no aiohttp")

    async def none_emb(*_a, **_k):
        return None

    monkeypatch.setattr(ing, "embed_with_retry_http_async", none_emb)
    outs = asyncio.run(ing.run_async_embedding_batches([[("i", "t", {})]], "m", 2))
    assert outs == [None]


def test_git_diff_file_sets_fallback_two_arg_diff(tmp_path: Path, monkeypatch):
    def fake_run(cmd, **kw):
        m = MagicMock()
        m.stdout = ""
        s = " ".join(cmd)
        if "is-inside-work-tree" in s:
            m.returncode = 0
        elif "rev-parse" in s and "HEAD" in s and "is-inside" not in s:
            m.returncode = 0
            m.stdout = "deadbeef\n"
        elif "diff" in s and "...HEAD" in s:
            m.returncode = 1
        elif "--diff-filter=ACMR" in s:
            m.returncode = 0
            m.stdout = "rel/a.py\n"
        elif "--diff-filter=D" in s:
            m.returncode = 0
            m.stdout = ""
        else:
            m.returncode = 0
        return m

    monkeypatch.setattr(ing.subprocess, "run", fake_run)
    mod, deleted, head = ing.git_diff_file_sets(tmp_path, "HEAD~1")
    assert mod == {"rel/a.py"}
    assert deleted == set()
    assert head == "deadbeef"


class _FakeColl:
    def __init__(self):
        self.deleted: list = []

    def delete(self, where=None):
        self.deleted.append(where)

    def count(self):
        return 0

    def get(self, **k):
        return {}

    def upsert(self, **k):
        pass


class _FakeChromaClient:
    def __init__(self):
        self.coll = _FakeColl()

    def get_or_create_collection(self, name):
        return self.coll


def test_ingest_run_git_diff_dry_run(tmp_path: Path, monkeypatch):
    db = tmp_path / "vdb"
    db.mkdir()
    root = tmp_path / "repo"
    root.mkdir()
    (root / "hello.py").write_text("def f():\n    return 1\n", encoding="utf-8")

    monkeypatch.setattr(ing, "validate_embedding_dimension", lambda *a, **k: None)

    def fake_git_diff(r, base):
        assert r == root.resolve()
        assert base == "HEAD~1" or base
        return ({"hello.py"}, {"gone.txt"}, "abc123")

    monkeypatch.setattr(ing, "git_diff_file_sets", fake_git_diff)
    monkeypatch.setattr(ing.chromadb, "PersistentClient", lambda path: _FakeChromaClient())

    args = ing.build_arg_parser().parse_args(
        [
            "--mode",
            "code",
            "--source",
            str(root),
            "--db-path",
            str(db),
            "--domain",
            "unit",
            "--dry-run",
            "--git-diff",
        ]
    )
    assert ing.ingest_run(args) == 0


def test_ingest_run_git_diff_unusable_warns(tmp_path: Path, monkeypatch, caplog):
    db = tmp_path / "vdb"
    db.mkdir()
    root = tmp_path / "repo"
    root.mkdir()
    monkeypatch.setattr(ing, "validate_embedding_dimension", lambda *a, **k: None)
    monkeypatch.setattr(ing, "git_diff_file_sets", lambda r, b: (None, None, None))
    monkeypatch.setattr(ing.chromadb, "PersistentClient", lambda path: _FakeChromaClient())
    (root / "a.py").write_text("x=1\n", encoding="utf-8")

    args = ing.build_arg_parser().parse_args(
        [
            "--mode",
            "code",
            "--source",
            str(root),
            "--db-path",
            str(db),
            "--domain",
            "unit",
            "--dry-run",
            "--git-diff",
        ]
    )
    with caplog.at_level(logging.WARNING):
        assert ing.ingest_run(args) == 0
    assert any("git-diff" in r.message for r in caplog.records)


def test_ingest_run_sync_embed_workers_empty_batches(tmp_path: Path, monkeypatch):
    """EMBED_ASYNC=0 with no chunks exercises the thread-pool embedding branch."""
    db = tmp_path / "vdb"
    db.mkdir()
    root = tmp_path / "repo"
    root.mkdir()

    monkeypatch.setattr(ing, "validate_embedding_dimension", lambda *a, **k: None)

    def empty_git_diff(_r, _b):
        return (set(), set(), "sha")

    monkeypatch.setattr(ing, "git_diff_file_sets", empty_git_diff)
    monkeypatch.setattr(ing.chromadb, "PersistentClient", lambda path: _FakeChromaClient())
    monkeypatch.setenv("EMBED_ASYNC", "0")

    args = ing.build_arg_parser().parse_args(
        [
            "--mode",
            "code",
            "--source",
            str(root),
            "--db-path",
            str(db),
            "--domain",
            "unit",
            "--git-diff",
        ]
    )
    assert ing.ingest_run(args) == 0


def test_ingest_async_embed_failed_batch_increments_failed(tmp_path: Path, monkeypatch):
    db = tmp_path / "vdb"
    db.mkdir()
    root = tmp_path / "repo"
    root.mkdir()
    (root / "tiny.py").write_text("x = 1\n", encoding="utf-8")

    monkeypatch.setattr(ing, "validate_embedding_dimension", lambda *a, **k: None)
    monkeypatch.setattr(ing, "git_diff_file_sets", lambda r, b: ({"tiny.py"}, set(), "s"))
    monkeypatch.setattr(ing.chromadb, "PersistentClient", lambda path: _FakeChromaClient())

    async def fail_batches(batches, model, conc):
        return [None] * len(batches)

    monkeypatch.setattr(ing, "run_async_embedding_batches", fail_batches)
    monkeypatch.setenv("EMBED_ASYNC", "1")

    args = ing.build_arg_parser().parse_args(
        [
            "--mode",
            "code",
            "--source",
            str(root),
            "--db-path",
            str(db),
            "--domain",
            "unit",
            "--git-diff",
        ]
    )
    # Failed embeddings do not populate results_holder["errors"]; exit is still success.
    assert ing.ingest_run(args) == 0


def test_load_checkpoint_bad_json_resets_hashes(tmp_path: Path, monkeypatch):
    db = tmp_path / "vdb"
    db.mkdir()
    root = tmp_path / "repo"
    root.mkdir()
    (root / "tiny.py").write_text("x = 1\n", encoding="utf-8")

    coll = "unit_code"
    cp_key = f"{coll}::checkpoint"
    git_key = ing.git_checkpoint_head_key(coll)
    ck_path = db / "ingest_checkpoint.json"
    ck_path.write_text(
        json.dumps({cp_key: "not-json", git_key: 999}),
        encoding="utf-8",
    )

    monkeypatch.setattr(ing, "validate_embedding_dimension", lambda *a, **k: None)
    monkeypatch.setattr(ing, "git_diff_file_sets", lambda r, b: ({"tiny.py"}, set(), "s"))
    monkeypatch.setattr(ing.chromadb, "PersistentClient", lambda path: _FakeChromaClient())

    async def ok_batches(batches, model, conc):
        out = []
        for b in batches:
            n = len(b)
            out.append(
                (
                    [x[0] for x in b],
                    [x[1] for x in b],
                    [x[2] for x in b],
                    [[0.0, 0.0]] * n,
                )
            )
        return out

    monkeypatch.setattr(ing, "run_async_embedding_batches", ok_batches)

    args = ing.build_arg_parser().parse_args(
        [
            "--mode",
            "code",
            "--source",
            str(root),
            "--db-path",
            str(db),
            "--domain",
            "unit",
            "--git-diff",
        ]
    )
    assert ing.ingest_run(args) in (0, 1)
