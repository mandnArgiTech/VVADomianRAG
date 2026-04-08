#!/usr/bin/env python3
"""
gui_backend.py — FastAPI bridge between the Enterprise Code Intelligence Dashboard
and ingest.py / query.py. Does not modify core RAG logic.

Run from the repository root:
  pip install fastapi uvicorn
  uvicorn gui_backend:app --host 127.0.0.1 --port 8501

Environment:
  RAG_GUI_DB_PATH      — Chroma folder (parent must exist; the app does not create random folders here).
                         Default when unset: Studio-Portable-RAG/VectorDB under this repo.
  RAG_GUI_SOURCE_BASE  — Root for /api/browse (default: Studio-Portable-RAG/Codebase or ./Codebase)
  RAG_REWRITE_MODEL    — Optional Ollama model for follow-up query rewrite only (ignored for Claude/DeepSeek rewrites).
  RAG_AGENT_WORKSPACE  — Default root for POST /api/agent file tools when request workspace is empty.
  RAG_AGENT_MAX_ITER   — Default max ReAct iterations (1–25; server hard-caps at 25).
  RAG_AGENT_CMD_TIMEOUT — Shell tool timeout seconds (default 30).
  RAG_AGENT_CTX_LIMIT  — Approximate token budget for context truncation heuristics (default 32000).
  RAG_AGENT_ALLOW_SHELL — If 0/false/no/off, disables run_terminal_command (default: enabled).

  GET /api/agent/tool-schemas — OpenAI-style JSON tool definitions for integrations (Ollama agent
  uses <tool_call> text tags; Anthropic and DeepSeek use native tool calling in the ReAct loop).

  GET /api/file/raw — Raw UTF-8 file under RAG_GUI_SOURCE_BASE (Chunk Inspector).
  GET /api/chunks/file — Chroma chunks for a file path (metadata source match).

  GET /api/vision/status — Docling/Pillow availability for the Vision Parser tab.
  POST /api/vision/parse — multipart PDF upload; streams SSE JSON events from util.universal_vision_parser.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import queue
import re
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Literal, Optional, Tuple, Union
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field, field_validator

# Repo root = directory containing this file (ingest.py, query.py, hybrid_search.py live here)
REPO_ROOT = Path(__file__).resolve().parent

log = logging.getLogger("gui_backend")

# -----------------------------------------------------------------------------
# Optional query engine (lazy import errors surfaced at request time)
# -----------------------------------------------------------------------------
query_mod: Any = None

try:
    import query as query_mod  # type: ignore[assignment]
except Exception as exc:  # pragma: no cover
    log.warning("query.py import failed (dashboard query features disabled): %s", exc)
    query_mod = None

QUERY_MAX_K = int(getattr(query_mod, "MAX_K", 25)) if query_mod is not None else 25

DEFAULT_DASHBOARD_LLM = (
    os.environ.get("RAG_LLM_MODEL", "").strip() or "qwen2.5-coder:32b"
)

# Optional smaller/faster model for query rewrite only (avoids slow rewrites on large chat models).
RAG_REWRITE_MODEL = os.environ.get("RAG_REWRITE_MODEL", "").strip()

try:
    import anthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:  # pragma: no cover
    anthropic = None  # type: ignore[assignment]
    ANTHROPIC_AVAILABLE = False

try:
    from openai import OpenAI

    OPENAI_SDK_AVAILABLE = True
except ImportError:  # pragma: no cover
    OpenAI = None  # type: ignore[misc, assignment]
    OPENAI_SDK_AVAILABLE = False

from agent_tools import (
    AgentSession,
    ToolResult,
    TOOL_REGISTRY,
    is_agent_shell_enabled,
    tool_descriptions_for_agent_prompt,
)


def _agent_tool_param_schema(
    properties: Dict[str, Any], required: List[str]
) -> Dict[str, Any]:
    return {"type": "object", "properties": properties, "required": required}


def openai_style_agent_tool_schemas() -> List[Dict[str, Any]]:
    """OpenAI Chat Completions ``tools`` shape (HTTP schema + DeepSeek native loop)."""
    str_p = {"type": "string", "description": "Parameter."}
    return [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read a workspace file; lines are 1-indexed.",
                "parameters": _agent_tool_param_schema(
                    {
                        "filepath": {**str_p, "description": "Path relative to workspace root."},
                        "start_line": {"type": "integer"},
                        "end_line": {"type": "integer"},
                    },
                    ["filepath"],
                ),
            },
        },
        {
            "type": "function",
            "function": {
                "name": "edit_file",
                "description": "Replace an exact substring in a file; include surrounding lines for uniqueness.",
                "parameters": _agent_tool_param_schema(
                    {
                        "filepath": str_p,
                        "search_block": str_p,
                        "replace_block": str_p,
                    },
                    ["filepath", "search_block", "replace_block"],
                ),
            },
        },
        {
            "type": "function",
            "function": {
                "name": "create_file",
                "description": "Create a new file under the workspace (fails if it exists).",
                "parameters": _agent_tool_param_schema(
                    {"filepath": str_p, "content": str_p},
                    ["filepath", "content"],
                ),
            },
        },
        {
            "type": "function",
            "function": {
                "name": "run_terminal_command",
                "description": "Run a shell command (optional cwd relative to workspace). May be disabled server-side.",
                "parameters": _agent_tool_param_schema(
                    {
                        "command": str_p,
                        "cwd": str_p,
                        "timeout": {"type": "number"},
                    },
                    ["command"],
                ),
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search_codebase",
                "description": "Hybrid RAG search over ingested collections.",
                "parameters": _agent_tool_param_schema(
                    {
                        "query": str_p,
                        "domain": str_p,
                        "top_k": {"type": "integer"},
                        "search_type": {
                            "type": "string",
                            "enum": ["auto", "code", "domain", "troubleshoot", "reference"],
                        },
                    },
                    ["query"],
                ),
            },
        },
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Web search (ddgs or duckduckgo-search).",
                "parameters": _agent_tool_param_schema(
                    {
                        "query": str_p,
                        "max_results": {"type": "integer"},
                    },
                    ["query"],
                ),
            },
        },
        {
            "type": "function",
            "function": {
                "name": "remember_concept",
                "description": "Persist markdown to Studio-Portable-RAG/DomainDocs or Wiki and ingest into Chroma.",
                "parameters": _agent_tool_param_schema(
                    {
                        "title": str_p,
                        "content": str_p,
                        "domain": str_p,
                        "storage": {
                            "type": "string",
                            "enum": ["domain_docs", "wiki"],
                            "description": "domain_docs (default) or wiki",
                        },
                    },
                    ["title", "content"],
                ),
            },
        },
    ]


def _agent_tools_openai_style() -> List[Dict[str, Any]]:
    """OpenAI ``tools`` list for agent loop; omits shell tool when disabled."""
    tools = openai_style_agent_tool_schemas()
    if not is_agent_shell_enabled():
        tools = [
            t for t in tools if t.get("function", {}).get("name") != "run_terminal_command"
        ]
    return tools


def _anthropic_tool_schemas() -> List[Dict[str, Any]]:
    """Anthropic Messages API ``tools`` entries derived from OpenAI-style schemas."""
    return [
        {
            "name": t["function"]["name"],
            "description": t["function"]["description"],
            "input_schema": t["function"]["parameters"],
        }
        for t in _agent_tools_openai_style()
    ]


# -----------------------------------------------------------------------------
# ANSI stripping for ingest terminal output (tqdm, etc.)
# -----------------------------------------------------------------------------
ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]|\x1b\][^\x07]*\x07|\r")


def strip_ansi(text: str) -> str:
    return ANSI_ESCAPE.sub("", text)


# -----------------------------------------------------------------------------
# Paths from environment
# -----------------------------------------------------------------------------


def _default_vector_db_dir() -> Path:
    d = (REPO_ROOT / "Studio-Portable-RAG" / "VectorDB").resolve()
    d.mkdir(parents=True, exist_ok=True)
    return d


def resolve_db_path(*, form_path: Optional[str] = None) -> str:
    """
    Vector database folder path.
    - Dashboard form override: create folder if parent exists (user picked path on purpose).
    - RAG_GUI_DB_PATH: never auto-create here (stops one-off typos from making empty folders).
    - Default: Studio-Portable-RAG/VectorDB under repo (created if missing).
    """
    if form_path and str(form_path).strip():
        p = Path(form_path.strip()).expanduser().resolve()
        if not p.parent.is_dir():
            raise HTTPException(
                status_code=400,
                detail=(
                    "The database path is wrong: the parent folder does not exist. "
                    "Fix the path or create the parent folder first."
                ),
            )
        p.mkdir(parents=True, exist_ok=True)
        return str(p)
    env_raw = os.environ.get("RAG_GUI_DB_PATH", "").strip()
    if env_raw:
        p = Path(env_raw).expanduser().resolve()
        if not p.parent.is_dir():
            raise HTTPException(
                status_code=400,
                detail=(
                    "Environment variable RAG_GUI_DB_PATH is wrong: its parent folder does not exist. "
                    "Fix the variable or create that parent folder."
                ),
            )
        return str(p)
    return str(_default_vector_db_dir())


def resolved_source_base() -> Path:
    raw = os.environ.get("RAG_GUI_SOURCE_BASE", "").strip()
    if raw:
        p = Path(raw).expanduser().resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p
    for candidate in (
        REPO_ROOT / "Studio-Portable-RAG" / "Codebase",
        REPO_ROOT / "Codebase",
    ):
        if candidate.is_dir():
            return candidate.resolve()
    fallback = (REPO_ROOT / "Codebase").resolve()
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def resolve_agent_workspace(raw: str) -> Path:
    """Agent sandbox root: explicit path in request, else RAG_AGENT_WORKSPACE, else repo root."""
    if raw.strip():
        return Path(raw.strip()).expanduser().resolve()
    env = os.environ.get("RAG_AGENT_WORKSPACE", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return REPO_ROOT


def safe_subpath(root: Path, rel: str) -> Path:
    """Resolve rel under root; reject path traversal (including odd Windows paths)."""
    root = root.resolve()
    if not root.is_dir():
        root.mkdir(parents=True, exist_ok=True)
    piece = rel.strip().replace("\\", "/").lstrip("/")
    if ".." in Path(piece).parts:
        raise HTTPException(status_code=400, detail="Path cannot use ..")
    target = (root / piece).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="That path is outside the allowed browse folder.",
        ) from exc
    return target


# -----------------------------------------------------------------------------
# Chroma connection cache (invalidated after ingest to reduce SQLite lock issues)
# -----------------------------------------------------------------------------
_chroma_lock = asyncio.Lock()
_chroma_state: Dict[str, Any] = {
    "client": None,
    "embedder": None,
    "cmap": None,
    "db_path": None,
    "model": None,
}


async def invalidate_chroma_cache() -> None:
    async with _chroma_lock:
        _chroma_state["client"] = None
        _chroma_state["embedder"] = None
        _chroma_state["cmap"] = None
        _chroma_state["db_path"] = None
        _chroma_state["model"] = None


async def ensure_chroma(db_path: str) -> Tuple[Any, Any, Dict[str, Any], str]:
    if query_mod is None:
        raise HTTPException(status_code=503, detail="query.py unavailable")

    async with _chroma_lock:
        model_env = os.environ.get("EMBEDDING_MODEL", "").strip()
        if not model_env:
            model_env = await asyncio.to_thread(query_mod.detect_embedding_model, db_path)
        need = (
            _chroma_state["cmap"] is None
            or _chroma_state["db_path"] != db_path
            or _chroma_state["model"] != model_env
        )
        if need:
            last_exc: Optional[BaseException] = None
            client = embedder = cmap = None
            for attempt in range(12):
                try:

                    def _connect() -> Tuple[Any, Any, Dict[str, Any]]:
                        return query_mod.connect_chroma_with_retry(db_path, model_env)

                    client, embedder, cmap = await asyncio.to_thread(_connect)
                    last_exc = None
                    break
                except Exception as exc:
                    last_exc = exc
                    msg = str(exc).lower()
                    if "locked" in msg or "busy" in msg:
                        await asyncio.sleep(0.2 * (attempt + 1))
                        continue
                    raise
            if last_exc is not None:
                raise HTTPException(
                    status_code=503,
                    detail=(
                        "The vector database is locked (often because ingestion is still writing). "
                        "Wait a few seconds and try again."
                    ),
                ) from last_exc
            _chroma_state.update(
                client=client,
                embedder=embedder,
                cmap=cmap,
                db_path=db_path,
                model=model_env,
            )
        return (
            _chroma_state["client"],
            _chroma_state["embedder"],
            _chroma_state["cmap"],
            _chroma_state["model"],
        )


# -----------------------------------------------------------------------------
# Ingest subprocess (single-flight + cancel)
# -----------------------------------------------------------------------------
_ingest_lock = threading.Lock()
_ingest_proc: Optional[subprocess.Popen] = None
_ingest_busy = False

_vision_lock = threading.Lock()
_vision_busy = False

MAX_VISION_PDF_BYTES = 80 * 1024 * 1024


def _reject_query_while_ingesting() -> None:
    with _ingest_lock:
        if _ingest_busy:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Ingestion is still running. Wait until it finishes, then search or chat again."
                ),
            )


class IngestBody(BaseModel):
    mode: Optional[str] = None
    source: Optional[str] = None
    domain: str = "general"
    collection: Optional[str] = None
    db_path: Optional[str] = None
    rally_project: Optional[str] = None
    rally_filter: Optional[str] = None
    confluence_space: Optional[str] = None
    confluence_label: Optional[str] = None
    concept_registry: Optional[str] = None
    git_diff: bool = False
    git_diff_base: Optional[str] = None
    dry_run: bool = False
    force: bool = False
    clean_stale: bool = False
    recreate_collection: bool = False
    mib_keep_deprecated: bool = False
    verbose: bool = False


def build_ingest_argv(body: IngestBody) -> List[str]:
    script = REPO_ROOT / "ingest.py"
    if not script.is_file():
        raise HTTPException(status_code=500, detail="ingest.py not found in repo root")
    args: List[str] = [str(script)]
    if body.mode:
        args += ["--mode", body.mode]
    if body.domain:
        args += ["--domain", body.domain]
    if body.collection:
        args += ["--collection", body.collection]
    db = resolve_db_path(form_path=body.db_path)
    args += ["--db-path", db]
    if body.source and body.mode and body.mode != "status":
        args += ["--source", body.source]
    if body.rally_project:
        args += ["--rally-project", body.rally_project]
    if body.rally_filter:
        args += ["--rally-filter", body.rally_filter]
    if body.confluence_space:
        args += ["--confluence-space", body.confluence_space]
    if body.confluence_label:
        args += ["--confluence-label", body.confluence_label]
    if body.concept_registry:
        args += ["--concept-registry", body.concept_registry]
    if body.git_diff:
        args.append("--git-diff")
    if body.git_diff_base:
        args += ["--git-diff-base", body.git_diff_base]
    if body.dry_run:
        args.append("--dry-run")
    if body.force:
        args.append("--force")
    if body.clean_stale:
        args.append("--clean-stale")
    if body.recreate_collection:
        args.append("--recreate-collection")
    if body.mib_keep_deprecated:
        args.append("--mib-keep-deprecated")
    if body.verbose:
        args.append("--verbose")
    return args


# -----------------------------------------------------------------------------
# Query API models
# -----------------------------------------------------------------------------


class QueryBody(BaseModel):
    query: str = Field(..., min_length=1)
    mode: str = "semantic"  # semantic | concept | codebase
    search_type: str = "auto"
    domain: str = ""
    repo: str = ""
    top_k: int = Field(5, ge=1, le=QUERY_MAX_K)
    chat: bool = False
    llm_provider: Literal["ollama", "anthropic", "deepseek"] = "ollama"
    llm_model: str = Field(default=DEFAULT_DASHBOARD_LLM)
    api_key: str = Field(default="", description="Anthropic or DeepSeek API key when not using Ollama")
    system_prompt: str = ""
    timeout: int = Field(120, ge=1, le=600)
    history: List[Dict[str, str]] = Field(default_factory=list)

    @field_validator("history", mode="before")
    @classmethod
    def sanitize_history(cls, v: Any) -> List[Dict[str, str]]:
        if not v:
            return []
        if not isinstance(v, list):
            return []
        out: List[Dict[str, str]] = []
        for item in v[-24:]:
            if not isinstance(item, dict):
                continue
            role = (item.get("role") or "").strip().lower()
            content = str(item.get("content") or "")[:8000]
            if role not in ("user", "assistant"):
                continue
            out.append({"role": role, "content": content})
        return out[-20:]


_SENTINEL = object()


@dataclass
class _NativeToolCall:
    """Emitted by cloud LLM iterators after streaming completes (one tool per step)."""

    name: str
    kwargs: Dict[str, Any]
    tool_call_id: str
    text_before: str


def _run_search_sync(
    db_path: str,
    qtext: str,
    mode: str,
    search_type: str,
    domain: str,
    repo: str,
    top_k: int,
    cmap: Dict[str, Any],
) -> List[Any]:
    if query_mod is None:
        return []
    if not cmap:
        return []
    k = max(1, min(int(top_k), query_mod.MAX_K))
    if mode == "concept":
        return query_mod.concept_search_hits(qtext, domain, cmap)
    effective_type = "code" if mode == "codebase" else search_type
    return query_mod._sync_multi_search(
        qtext, k, effective_type, domain, repo, cmap, db_path
    )


async def run_search(
    body: QueryBody,
    db_path: str,
    cmap: Dict[str, Any],
    search_query: Optional[str] = None,
) -> List[Any]:
    """Run hybrid/concept search without SIGALRM; retry briefly if SQLite reports locked/busy."""
    qtext = (search_query or body.query).strip()

    def _call() -> List[Any]:
        last: Optional[Exception] = None
        for attempt in range(15):
            try:
                return _run_search_sync(
                    db_path,
                    qtext,
                    body.mode,
                    body.search_type,
                    body.domain,
                    body.repo,
                    body.top_k,
                    cmap,
                )
            except Exception as exc:
                last = exc
                msg = str(exc).lower()
                if "locked" in msg or "busy" in msg:
                    time.sleep(0.12 * (attempt + 1))
                    continue
                raise
        if last is not None:
            raise last
        raise RuntimeError("Search failed after retries")

    return await asyncio.wait_for(asyncio.to_thread(_call), timeout=float(body.timeout))


def _iter_llm_tokens(
    user_query: str,
    hits: List[Any],
    llm_model: str,
    system_prompt: str,
    history_messages: Optional[List[Dict[str, str]]],
    extra_context: str = "",
) -> Any:
    """Sync generator of token strings; empty if ollama missing or error."""
    if query_mod is None or not getattr(query_mod, "OLLAMA_LIB_AVAILABLE", False):
        yield from ()
        return
    om = getattr(query_mod, "_ollama_mod", None)
    if om is None:
        yield from ()
        return
    ctx = query_mod._build_context_blocks(hits)
    if extra_context.strip():
        ctx = f"{ctx}\n\n## Additional Web Context\n{extra_context.strip()}"
    sp = (system_prompt or "").strip() or query_mod.DEFAULT_SYSTEM_PROMPT
    messages: List[Dict[str, str]] = [{"role": "system", "content": sp}]
    if history_messages:
        messages.extend(history_messages)
    messages.append(
        {
            "role": "user",
            "content": f"Context:\n\n{ctx}\n\n---\n\nQuestion: {user_query}",
        }
    )
    try:
        stream = om.chat(model=llm_model, messages=messages, stream=True)
    except Exception as exc:
        log.warning("ollama.chat failed: %s", exc)
        yield from ()
        return
    try:
        for chunk in stream:
            tok = query_mod._stream_chunk_text(chunk)
            if tok:
                yield tok
    except Exception as exc:
        log.warning("LLM stream error: %s", exc)


async def async_token_stream(
    user_query: str,
    hits: List[Any],
    llm_model: str,
    system_prompt: str,
    history_messages: Optional[List[Dict[str, str]]],
    extra_context: str = "",
) -> AsyncIterator[str]:
    it = iter(
        _iter_llm_tokens(
            user_query, hits, llm_model, system_prompt, history_messages, extra_context
        )
    )

    def _next() -> Any:
        try:
            return next(it)
        except StopIteration:
            return _SENTINEL

    while True:
        tok = await asyncio.to_thread(_next)
        if tok is _SENTINEL:
            break
        yield str(tok)


def _iter_anthropic_text(
    system: str,
    messages: List[Dict[str, str]],
    model: str,
    api_key: str,
) -> Any:
    if not ANTHROPIC_AVAILABLE or anthropic is None:
        yield "Error: install anthropic (pip install anthropic)."
        return
    client = anthropic.Anthropic(api_key=api_key)
    amsg = [{"role": m["role"], "content": m["content"]} for m in messages]
    with client.messages.stream(
        model=model,
        max_tokens=8192,
        system=system,
        messages=amsg,
    ) as stream:
        for text in stream.text_stream:
            yield text


def _iter_deepseek_text(
    system: str,
    messages: List[Dict[str, str]],
    model: str,
    api_key: str,
) -> Any:
    if not OPENAI_SDK_AVAILABLE or OpenAI is None:
        yield "Error: install openai (pip install openai)."
        return
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    oa: List[Dict[str, str]] = [{"role": "system", "content": system}]
    oa.extend({"role": m["role"], "content": m["content"]} for m in messages)
    stream = client.chat.completions.create(
        model=model or "deepseek-chat",
        messages=oa,
        stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta
        if delta and getattr(delta, "content", None):
            yield delta.content


async def _async_from_sync_text_iterator(sync_iter_factory: Any) -> AsyncIterator[str]:
    it = iter(sync_iter_factory())

    def _step() -> Any:
        try:
            return next(it)
        except StopIteration:
            return _SENTINEL

    while True:
        piece = await asyncio.to_thread(_step)
        if piece is _SENTINEL:
            break
        yield str(piece)


async def stream_chat_tokens(
    body: QueryBody,
    hits: List[Any],
    extra_context: str = "",
    *,
    user_query_for_llm: Optional[str] = None,
) -> AsyncIterator[str]:
    """Stream answer tokens from Ollama, Claude (Anthropic), or DeepSeek."""
    if query_mod is None:
        return
    user_q = (user_query_for_llm if user_query_for_llm is not None else body.query).strip()

    if body.llm_provider == "ollama":
        async for tok in async_token_stream(
            user_q,
            hits,
            body.llm_model,
            body.system_prompt,
            body.history or None,
            extra_context or "",
        ):
            yield tok
        return

    ctx = await asyncio.to_thread(query_mod._build_context_blocks, hits)
    if extra_context:
        ctx = f"{ctx}\n\n## Additional Web Context\n{extra_context}"
    sp = (body.system_prompt or "").strip() or query_mod.DEFAULT_SYSTEM_PROMPT
    user_block = f"Context:\n\n{ctx}\n\n---\n\nQuestion: {user_q}"
    msgs: List[Dict[str, str]] = []
    for h in body.history or []:
        msgs.append({"role": h["role"], "content": h["content"]})
    msgs.append({"role": "user", "content": user_block})
    key = (body.api_key or "").strip()

    if body.llm_provider == "anthropic":
        if not key:
            yield "Error: enter your Anthropic API key in the dashboard, or switch to Local Ollama."
            return

        async for tok in _async_from_sync_text_iterator(
            lambda: _iter_anthropic_text(sp, msgs, body.llm_model, key)
        ):
            yield tok
        return

    if body.llm_provider == "deepseek":
        if not key:
            yield "Error: enter your DeepSeek API key in the dashboard, or switch to Local Ollama."
            return

        async for tok in _async_from_sync_text_iterator(
            lambda: _iter_deepseek_text(sp, msgs, body.llm_model, key)
        ):
            yield tok


# -----------------------------------------------------------------------------
# FastAPI app
# -----------------------------------------------------------------------------
app = FastAPI(
    title="DomainRAG Dashboard API",
    description="Local bridge for ingest.py and query.py",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_static_dir = REPO_ROOT / "static"
if _static_dir.is_dir():
    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, (HTTPException, RequestValidationError)):
        raise exc
    log.exception("Unhandled error: %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc) or "Internal server error"},
    )


@app.get("/")
async def root() -> FileResponse:
    index = REPO_ROOT / "index.html"
    if not index.is_file():
        raise HTTPException(status_code=404, detail="index.html not found next to gui_backend.py")
    return FileResponse(index)


@app.get("/api/status")
async def api_status() -> Dict[str, Any]:
    if query_mod is None:
        raise HTTPException(status_code=503, detail="query.py unavailable")
    env_db = os.environ.get("RAG_GUI_DB_PATH", "").strip()
    db_path = resolve_db_path()
    db_path_source = "env" if env_db else "default"
    text = await asyncio.to_thread(query_mod.run_status, db_path)
    with _ingest_lock:
        ingesting = _ingest_busy
    env_ws = os.environ.get("RAG_AGENT_WORKSPACE", "").strip()
    ollama_ok = False
    if query_mod is not None:
        ollama_ok = await asyncio.to_thread(query_mod.check_ollama)
    return {
        "db_path": db_path,
        "db_path_source": db_path_source,
        "rag_gui_db_path": env_db or None,
        "status": text,
        "ingest_running": ingesting,
        "agent_running": _agent_busy,
        "workspace_root": str(REPO_ROOT),
        "agent_default_workspace": str(resolve_agent_workspace("")),
        "rag_agent_workspace_env": env_ws or None,
        "agent_shell_enabled": is_agent_shell_enabled(),
        "ollama_reachable": ollama_ok,
        "vision_running": _vision_busy,
    }


@app.get("/api/browse")
async def api_browse(path: str = "") -> Dict[str, Any]:
    root = resolved_source_base()
    target = safe_subpath(root, path)
    if not target.exists():
        return {"root": str(root), "path": path, "entries": []}
    if target.is_file():
        return {
            "root": str(root),
            "path": path,
            "entries": [{"name": target.name, "type": "file", "path": path}],
        }
    entries = []
    try:
        for child in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
            rel = str(Path(path) / child.name) if path else child.name
            entries.append(
                {
                    "name": child.name,
                    "type": "directory" if child.is_dir() else "file",
                    "path": rel.replace("\\", "/"),
                }
            )
    except OSError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"root": str(root), "path": path, "entries": entries}


@app.get("/api/file/raw")
async def api_file_raw(path: str) -> PlainTextResponse:
    """Return raw UTF-8 text for a file under RAG_GUI_SOURCE_BASE (path relative to browse root)."""
    if not path.strip():
        raise HTTPException(status_code=400, detail="path query parameter is required")
    root = resolved_source_base()
    target = safe_subpath(root, path)
    if not target.is_file():
        raise HTTPException(status_code=404, detail=f"Not a file: {path}")
    try:
        text = target.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PlainTextResponse(content=text, media_type="text/plain; charset=utf-8")


@app.get("/api/chunks/file")
async def api_chunks_file(path: str, db_path: Optional[str] = None) -> JSONResponse:
    """List all Chroma chunks whose metadata source matches the resolved absolute file path."""
    if not path.strip():
        raise HTTPException(status_code=400, detail="path query parameter is required")
    root = resolved_source_base()
    abs_path = safe_subpath(root, path).resolve()
    if not abs_path.is_file():
        raise HTTPException(status_code=404, detail=f"Not a file: {path}")
    abs_src = str(abs_path)
    resolved = resolve_db_path(form_path=db_path)
    _, _, cmap, _ = await ensure_chroma(resolved)
    chunks_out: List[Dict[str, Any]] = []
    for collection_name, collection in cmap.items():
        try:
            batch = await asyncio.to_thread(
                lambda c=collection: c.get(
                    where={"source": abs_src},
                    include=["ids", "documents", "metadatas"],
                )
            )
        except Exception as exc:  # pragma: no cover
            log.warning("chunks/file: collection %s get failed: %s", collection_name, exc)
            continue
        ids = batch.get("ids") or []
        docs = batch.get("documents") or []
        metas = batch.get("metadatas") or []
        for i, cid in enumerate(ids):
            doc = docs[i] if i < len(docs) else ""
            meta = metas[i] if i < len(metas) else {}
            if isinstance(meta, dict):
                meta_clean = jsonable_encoder(meta)
            else:
                meta_clean = {}
            chunks_out.append(
                {
                    "chunk_id": cid,
                    "text": doc if isinstance(doc, str) else (doc or ""),
                    "metadata": meta_clean,
                    "collection": collection_name,
                }
            )
    payload = {
        "file": path,
        "abs_source": abs_src,
        "total_chunks": len(chunks_out),
        "chunks": chunks_out,
    }
    return JSONResponse(content=payload)


@app.get("/api/vision/status")
async def api_vision_status() -> Dict[str, Any]:
    """Report Docling/Pillow availability and whether a vision parse is running."""
    try:
        from util.universal_vision_parser import check_vision_dependencies
    except ImportError as exc:
        return {
            "docling_available": False,
            "pillow_available": False,
            "vision_busy": False,
            "import_error": str(exc),
        }
    d = check_vision_dependencies()
    return {
        "docling_available": d.get("docling_available", False),
        "pillow_available": d.get("pillow_available", False),
        "vision_busy": _vision_busy,
    }


@app.post("/api/vision/parse")
async def api_vision_parse(
    file: UploadFile = File(...),
    vision_provider: str = Form("ollama"),
    custom_prompt: str = Form(""),
    vision_model: str = Form(""),
    api_key: str = Form(""),
) -> StreamingResponse:
    """Stream vision-augmented PDF parsing as SSE (JSON events per line)."""
    global _vision_busy

    if _agent_busy:
        raise HTTPException(
            status_code=409,
            detail="An agent session is running. Wait for it to finish before vision parsing.",
        )
    with _ingest_lock:
        if _ingest_busy:
            raise HTTPException(
                status_code=409,
                detail="Ingestion is running. Wait for it to finish before vision parsing.",
            )

    fname = (file.filename or "").strip().lower()
    if not fname.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Upload a PDF file (.pdf).")

    prov = (vision_provider or "ollama").strip().lower()
    if prov not in ("ollama", "anthropic", "openai"):
        raise HTTPException(status_code=400, detail="vision_provider must be ollama, anthropic, or openai.")

    if prov == "anthropic":
        if not ANTHROPIC_AVAILABLE:
            raise HTTPException(status_code=503, detail="Install anthropic: pip install anthropic")
        if not (api_key or "").strip():
            raise HTTPException(status_code=400, detail="Enter your Anthropic API key for vision parsing.")
    elif prov == "openai":
        if not OPENAI_SDK_AVAILABLE:
            raise HTTPException(status_code=503, detail="Install openai: pip install openai")
        if not (api_key or "").strip():
            raise HTTPException(status_code=400, detail="Enter your OpenAI API key for vision parsing.")
    elif prov == "ollama":
        if query_mod is None or not getattr(query_mod, "OLLAMA_LIB_AVAILABLE", False):
            raise HTTPException(
                status_code=503,
                detail="Ollama Python client unavailable; install ollama package.",
            )
        ollama_ok = await asyncio.to_thread(query_mod.check_ollama)
        if not ollama_ok:
            raise HTTPException(
                status_code=503,
                detail="Ollama is not reachable at http://127.0.0.1:11434 — start Ollama first.",
            )

    raw = await file.read()
    if len(raw) > MAX_VISION_PDF_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"PDF too large (max {MAX_VISION_PDF_BYTES // (1024 * 1024)} MB).",
        )

    if not _vision_lock.acquire(blocking=False):
        raise HTTPException(
            status_code=409,
            detail="Another vision parse is already running. Wait for it to finish.",
        )

    tmp_path: Optional[str] = None
    try:
        fd, tmp_path = tempfile.mkstemp(suffix=".pdf", prefix="vision_")
        os.close(fd)
        Path(tmp_path).write_bytes(raw)
    except Exception as exc:
        _vision_lock.release()
        raise HTTPException(status_code=500, detail=f"Could not save upload: {exc}") from exc

    kw = {
        "vision_provider": prov,
        "vision_model": (vision_model or "").strip(),
        "api_key": (api_key or "").strip(),
        "custom_prompt": (custom_prompt or "").strip(),
    }

    async def event_stream() -> AsyncIterator[str]:
        global _vision_busy
        _vision_busy = True
        q: "queue.Queue[Optional[Dict[str, Any]]]" = queue.Queue()

        def worker() -> None:
            try:
                from util.universal_vision_parser import parse_pdf_with_vision

                for ev in parse_pdf_with_vision(tmp_path or "", **kw):
                    q.put(ev)
            except Exception as exc:
                log.exception("Vision parse worker failed")
                q.put({"type": "error", "message": str(exc)})
            finally:
                q.put(None)

        threading.Thread(target=worker, daemon=True).start()
        try:
            while True:
                ev = await asyncio.to_thread(q.get)
                if ev is None:
                    break
                try:
                    payload = json.dumps(jsonable_encoder(ev))
                except Exception as ser_exc:
                    payload = json.dumps(
                        {"type": "error", "message": f"Serialize failed: {ser_exc}"}
                    )
                yield f"data: {payload}\n\n"
        finally:
            _vision_busy = False
            _vision_lock.release()
            try:
                if tmp_path and Path(tmp_path).is_file():
                    Path(tmp_path).unlink(missing_ok=True)
            except OSError as exc:
                log.warning("Could not remove temp PDF: %s", exc)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/api/ingest/cancel")
async def api_ingest_cancel() -> Dict[str, str]:
    global _ingest_proc, _ingest_busy
    with _ingest_lock:
        proc = _ingest_proc
    if proc is None or proc.poll() is not None:
        return {"detail": "no active ingest"}
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
    with _ingest_lock:
        _ingest_busy = False
        _ingest_proc = None
    return {"detail": "terminated"}


@app.post("/api/ingest")
async def api_ingest(body: IngestBody) -> StreamingResponse:
    global _ingest_proc, _ingest_busy

    if _vision_busy:
        raise HTTPException(
            status_code=409,
            detail="Vision PDF parsing is running. Wait for it to finish before ingesting.",
        )
    if _agent_busy:
        raise HTTPException(
            status_code=409,
            detail="An agent session is running. Wait for it to finish before ingesting.",
        )

    argv = build_ingest_argv(body)

    with _ingest_lock:
        if _ingest_busy:
            raise HTTPException(status_code=409, detail="An ingest job is already running")
        _ingest_busy = True

    async def event_stream() -> AsyncIterator[str]:
        global _ingest_proc, _ingest_busy
        proc: Optional[subprocess.Popen] = None
        try:
            proc = subprocess.Popen(
                [sys.executable, *argv],
                cwd=str(REPO_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env={**os.environ},
            )
            with _ingest_lock:
                _ingest_proc = proc

            assert proc.stdout is not None

            while True:
                line = await asyncio.to_thread(proc.stdout.readline)
                if not line:
                    break
                clean = strip_ansi(line.rstrip("\n\r"))
                yield f"data: {json.dumps({'line': clean})}\n\n"

            rest = await asyncio.to_thread(proc.stdout.read)
            if rest:
                for raw in rest.splitlines():
                    clean = strip_ansi(raw)
                    yield f"data: {json.dumps({'line': clean})}\n\n"

            code = await asyncio.to_thread(proc.wait)
            yield f"data: {json.dumps({'done': True, 'exit_code': int(code or 0)})}\n\n"
        except asyncio.CancelledError:
            if proc and proc.poll() is None:
                proc.terminate()
            raise
        except Exception as exc:
            log.exception("ingest stream error")
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"
            yield f"data: {json.dumps({'done': True, 'exit_code': 1})}\n\n"
        finally:
            with _ingest_lock:
                _ingest_busy = False
                _ingest_proc = None
            await invalidate_chroma_cache()

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# -----------------------------------------------------------------------------
# Query reformulation (standalone search query from chat history)
# -----------------------------------------------------------------------------

REWRITE_SYSTEM = (
    "You are a search query rewriter. Given the conversation history and the "
    "latest user message, rewrite the latest message into a single standalone "
    "search query that resolves all pronouns and references. "
    "Output ONLY the rewritten query string. No quotes, no explanation."
)

_REWRITE_PREFIXES = (
    "Rewritten query:",
    "Search query:",
    "Query:",
    "Here is the rewritten query:",
    "Here is the query:",
    "Here is",
)


def _sanitize_rewritten_query(result: str, raw_query: str) -> str:
    if not result or not result.strip():
        return raw_query
    result = result.strip().splitlines()[0].strip()
    prefixes = sorted(_REWRITE_PREFIXES, key=len, reverse=True)
    while True:
        stripped = False
        for prefix in prefixes:
            if result.lower().startswith(prefix.lower()):
                result = result[len(prefix) :].strip()
                stripped = True
                break
        if not stripped:
            break
    result = result.strip("\"'`")
    if not result or len(result) > 500:
        return raw_query
    log.info("Query rewrite: %r -> %r", raw_query, result)
    return result


def _rewrite_ollama_sync(messages: List[Dict[str, str]], eff_model: str) -> str:
    if query_mod is None or not getattr(query_mod, "OLLAMA_LIB_AVAILABLE", False):
        return ""
    om = getattr(query_mod, "_ollama_mod", None)
    if om is None:
        return ""
    try:
        resp = om.chat(model=eff_model, messages=messages, stream=False)
    except Exception as exc:
        log.warning("rewrite ollama.chat failed: %s", exc)
        return ""
    msg = getattr(resp, "message", None) or (
        resp.get("message") if isinstance(resp, dict) else None
    )
    text = (msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", "")) or ""
    return str(text).strip()


def _rewrite_anthropic_sync(
    history_tail: List[Dict[str, str]], user_line: str, eff_model: str, api_key: str
) -> str:
    if not ANTHROPIC_AVAILABLE or anthropic is None:
        return ""
    try:
        client = anthropic.Anthropic(api_key=api_key)
        msgs: List[Dict[str, Any]] = []
        for m in history_tail:
            msgs.append({"role": m["role"], "content": m["content"]})
        msgs.append({"role": "user", "content": user_line})
        r = client.messages.create(
            model=eff_model,
            max_tokens=256,
            system=REWRITE_SYSTEM,
            messages=msgs,
        )
        if r.content and getattr(r.content[0], "text", None):
            return str(r.content[0].text).strip()
    except Exception as exc:
        log.warning("rewrite anthropic failed: %s", exc)
    return ""


def _rewrite_deepseek_sync(
    messages: List[Dict[str, str]], eff_model: str, api_key: str
) -> str:
    if not OPENAI_SDK_AVAILABLE or OpenAI is None:
        return ""
    try:
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        r = client.chat.completions.create(
            model=eff_model or "deepseek-chat",
            messages=messages,
            max_tokens=256,
            stream=False,
        )
        ch = r.choices[0].message
        return str(getattr(ch, "content", None) or "").strip()
    except Exception as exc:
        log.warning("rewrite deepseek failed: %s", exc)
    return ""


async def rewrite_query(
    raw_query: str,
    history: List[Dict[str, str]],
    provider: str,
    model: str,
    api_key: str,
) -> str:
    raw = raw_query.strip()
    if len(history) < 2:
        return raw
    key = (api_key or "").strip()
    hist_tail = list(history[-6:])
    # RAG_REWRITE_MODEL is for Ollama only; never pass it to Anthropic/DeepSeek (wrong model IDs).
    ollama_rewrite_model = (RAG_REWRITE_MODEL or model or "").strip() or DEFAULT_DASHBOARD_LLM
    anthropic_rewrite_model = (model or "").strip() or "claude-3-5-haiku-20241022"
    deepseek_rewrite_model = (model or "").strip() or "deepseek-chat"

    async def _attempt() -> str:
        p = provider
        if p in ("anthropic", "deepseek") and not key:
            p = "ollama"
        if p == "ollama":
            msgs: List[Dict[str, str]] = (
                [{"role": "system", "content": REWRITE_SYSTEM}] + hist_tail + [{"role": "user", "content": raw}]
            )
            return await asyncio.to_thread(_rewrite_ollama_sync, msgs, ollama_rewrite_model)
        if p == "anthropic" and key:
            return await asyncio.to_thread(
                _rewrite_anthropic_sync, hist_tail, raw, anthropic_rewrite_model, key
            )
        if p == "deepseek" and key:
            oa: List[Dict[str, str]] = (
                [{"role": "system", "content": REWRITE_SYSTEM}]
                + hist_tail
                + [{"role": "user", "content": raw}]
            )
            return await asyncio.to_thread(_rewrite_deepseek_sync, oa, deepseek_rewrite_model, key)
        return ""

    try:
        text = await asyncio.wait_for(_attempt(), timeout=3.0)
    except asyncio.TimeoutError:
        log.warning("Query rewrite timed out, using original query")
        return raw
    except Exception as exc:
        log.warning("Query rewrite failed (%s), using original", exc)
        return raw
    return _sanitize_rewritten_query(text, raw)


@app.post("/api/query")
async def api_query(body: QueryBody) -> Any:
    if query_mod is None:
        raise HTTPException(status_code=503, detail="query.py unavailable")
    _reject_query_while_ingesting()
    if not await asyncio.to_thread(query_mod.check_ollama):
        raise HTTPException(
            status_code=503,
            detail="Ollama not reachable at http://127.0.0.1:11434 — start Ollama first",
        )

    db_path = resolve_db_path()
    _, _, cmap, _ = await ensure_chroma(db_path)
    if not cmap:
        raise HTTPException(
            status_code=400,
            detail="The vector database has no collections yet. Run ingestion first, then try again.",
        )

    if body.chat:
        if body.llm_provider == "anthropic":
            if not ANTHROPIC_AVAILABLE:
                raise HTTPException(
                    status_code=503,
                    detail="To use Claude, install: pip install anthropic",
                )
            if not (body.api_key or "").strip():
                raise HTTPException(
                    status_code=400,
                    detail="Enter your Anthropic API key, or switch the answer model to Local Ollama.",
                )
        elif body.llm_provider == "deepseek":
            if not OPENAI_SDK_AVAILABLE:
                raise HTTPException(
                    status_code=503,
                    detail="To use DeepSeek, install: pip install openai",
                )
            if not (body.api_key or "").strip():
                raise HTTPException(
                    status_code=400,
                    detail="Enter your DeepSeek API key, or switch the answer model to Local Ollama.",
                )

    raw_query = body.query.strip()
    cleaned_query, chat_mentions = parse_at_mentions(raw_query)
    search_query = cleaned_query or raw_query

    web_context = ""
    if "web" in chat_mentions:
        try:
            from agent_tools import web_search as _ws
            wr = await asyncio.to_thread(
                _ws,
                session=None,
                query=search_query,
            )
            if wr.success and wr.output:
                web_context = wr.output
        except Exception as exc:
            log.warning("@web pre-flight failed: %s", exc)

    if "docs" in chat_mentions:
        # Filter to domain-doc collections via search_type (not domain=domain_doc — that
        # substring does not match names like nms_domain; see query._select_collection_names).
        body.search_type = "domain"

    if body.history:
        search_query = await rewrite_query(
            search_query,
            body.history,
            body.llm_provider,
            body.llm_model,
            body.api_key,
        )

    try:
        hits = await run_search(body, db_path, cmap, search_query=search_query)
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail=f"Search took too long (over {body.timeout} seconds). Try a smaller scope or raise the timeout.",
        ) from None
    except Exception as exc:
        log.exception("Search failed")
        low = str(exc).lower()
        if "no collections" in low or "chroma" in low and "empty" in low:
            raise HTTPException(
                status_code=400,
                detail="Search could not run (empty or unreadable database). Run ingestion first.",
            ) from exc
        raise HTTPException(
            status_code=503,
            detail=f"Search failed: {exc!s}. If ingestion was running, wait and retry.",
        ) from exc

    results = jsonable_encoder([asdict(h) for h in hits])
    md_ctx = ""
    if hits:
        if body.mode == "concept":
            md_ctx = await asyncio.to_thread(
                query_mod.format_concept_markdown, hits, body.query.strip()
            )
        else:
            md_ctx = await asyncio.to_thread(query_mod.format_markdown, hits, body.query)

    if not body.chat:
        return JSONResponse(
            jsonable_encoder(
                {
                    "results": results,
                    "context_markdown": md_ctx,
                    "no_hits": len(hits) == 0,
                    "search_query": search_query,
                }
            )
        )

    if not hits:
        return JSONResponse(
            jsonable_encoder(
                {
                    "results": [],
                    "context_markdown": "",
                    "no_hits": True,
                    "answer": "",
                    "search_query": search_query,
                }
            )
        )

    async def sse_chat() -> AsyncIterator[str]:
        yield f"data: {json.dumps({'type': 'agent_action', 'action': 'search', 'query': search_query, 'original': raw_query})}\n\n"
        if web_context:
            yield f"data: {json.dumps({'type': 'agent_action', 'action': 'web_search', 'query': search_query})}\n\n"
        try:
            llm_q = (cleaned_query or raw_query) if chat_mentions else None
            async for tok in stream_chat_tokens(
                body,
                hits,
                extra_context=web_context,
                user_query_for_llm=llm_q,
            ):
                yield f"data: {json.dumps({'token': tok})}\n\n"
        except Exception as exc:
            log.exception("Chat stream failed")
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"
        try:
            done_payload = jsonable_encoder(
                {
                    "done": True,
                    "results": results,
                    "context_markdown": md_ctx,
                    "search_query": search_query,
                }
            )
            yield f"data: {json.dumps(done_payload)}\n\n"
        except Exception as exc:
            log.exception("SSE done payload failed")
            yield f"data: {json.dumps({'error': f'Serialize results failed: {exc!s}'})}\n\n"
            yield f"data: {json.dumps({'done': True, 'results': [], 'context_markdown': md_ctx, 'search_query': search_query})}\n\n"

    return StreamingResponse(sse_chat(), media_type="text/event-stream")


# =============================================================================
# Autonomous Coding Agent — ReAct execution engine
# =============================================================================

# ---------------------------------------------------------------------------
# Agent concurrency state
# ---------------------------------------------------------------------------
_agent_slot = threading.Lock()
_agent_busy = False
_agent_cancel = threading.Event()

_AGENT_MAX_ITER = int(os.environ.get("RAG_AGENT_MAX_ITER", "10"))
_AGENT_CTX_LIMIT = int(os.environ.get("RAG_AGENT_CTX_LIMIT", "32000"))

# ---------------------------------------------------------------------------
# Agent system prompt (Phase 3) — built per session so tool list matches RAG_AGENT_ALLOW_SHELL
# ---------------------------------------------------------------------------


def build_agent_system_prompt(provider: Literal["ollama", "anthropic", "deepseek"] = "ollama") -> str:
    desc = tool_descriptions_for_agent_prompt()
    shell_disabled = not is_agent_shell_enabled()
    verify_line = (
        "4. VERIFY: For CODE files (.py, .js, .c, etc.), run a verification command via run_terminal_command "
        "(e.g., syntax check, pytest). For MARKDOWN or DOC files, NO verification is needed."
        if not shell_disabled
        else "4. VERIFY: You cannot run shell commands on this server. After edits, reason about correctness from read_file output; state what the user should run locally to verify."
    )
    shell_security = """## Shell / safety (operators read this too)
Terminal access uses regex blocklists and a timeout only. This is NOT a full sandbox: clever or encoded commands may bypass checks. Do not use the agent on untrusted prompts on sensitive machines. Operators may set RAG_AGENT_ALLOW_SHELL=0 to remove run_terminal_command entirely.
"""
    no_shell_note = ""
    if shell_disabled:
        no_shell_note = "\n## run_terminal_command\nThis tool is **disabled** on this server. Use read_file, edit_file, create_file, search_codebase, web_search, and remember_concept. End with <task_complete> describing changes and suggested local verification commands.\n"

    if provider == "ollama":
        tool_usage = """## Tool usage
To use a tool, emit EXACTLY:
<tool_call>{{"name":"tool_name","kwargs":{{...}}}}</tool_call>

Rules:
- Only ONE tool call per response. Wait for the result before continuing.
- Tool results arrive as the next user message prefixed with [Tool Result: tool_name].
- NEVER emit <tool_call> inside a markdown code fence.
"""
        integrations = (
            "## Integrations\n"
            "- OpenAI-style tool JSON (for custom clients) is available at GET /api/agent/tool-schemas.\n"
            "- This Ollama session uses <tool_call> text tags in the ReAct loop.\n"
        )
    else:
        tool_usage = """## Tool usage
Native function tools are attached to this request. Call at most one tool per turn, then wait for the tool result message before continuing.
"""

        integrations = (
            "## Integrations\n"
            "- OpenAI-style tool JSON (for custom clients) is available at GET /api/agent/tool-schemas.\n"
            "- This session uses native tool calling (no <tool_call> XML).\n"
        )

    return f"""\
You are an autonomous coding agent. You work inside a single workspace root with the tools listed below.

{tool_usage}
## Available tools
{desc}
{no_shell_note}
{shell_security}
## Workflow
1. PLAN: Think step-by-step about how to accomplish the task.
2. SEARCH/READ: Use search_codebase, web_search, or read_file to gather context.
3. EDIT/CREATE: Use edit_file or create_file to make changes. Use remember_concept to save important findings to the RAG database for future retrieval.
{verify_line}
5. If verification fails (or you cannot verify), read outputs, fix, and repeat as needed.
6. COMPLETE: Once the files are written, you MUST immediately emit <task_complete>Summary of work</task_complete> to save your work. If you do not emit this tag, your files will be rolled back and deleted.

## edit_file rules
- search_block must be an EXACT substring of the current file content.
- Include 3-5 surrounding lines to make search_block unique.
- Never pass entire file contents as search_block.
- Always read_file first if you are unsure of the current content.

## web_search & remember_concept
- Use web_search when the user asks about external APIs, current best practices, or information not in the codebase.
- Use remember_concept to persist useful knowledge (architecture decisions, learned patterns, research findings) so future searches can retrieve it.
- remember_concept writes under Studio-Portable-RAG/DomainDocs by default; use kwargs \"storage\": \"wiki\" for Studio-Portable-RAG/Wiki instead.

{integrations}
## Important
- <task_complete> is the ONLY way to end the session. You MUST emit it when done.
- Never attempt destructive system commands. Respect tool errors.
- If you are stuck after multiple attempts, emit <task_complete> with an explanation of what failed.
"""

# ---------------------------------------------------------------------------
# Agent request model
# ---------------------------------------------------------------------------

class AgentBody(BaseModel):
    task: str = Field(..., min_length=1)
    workspace: str = Field(default="")
    llm_provider: Literal["ollama", "anthropic", "deepseek"] = "ollama"
    llm_model: str = Field(default=DEFAULT_DASHBOARD_LLM)
    api_key: str = ""
    max_iterations: int = Field(default=_AGENT_MAX_ITER, ge=1, le=25)
    db_path: Optional[str] = None


# ---------------------------------------------------------------------------
# Streaming buffer — suppresses <tool_call> / <task_complete> tags from UI
# ---------------------------------------------------------------------------

class StreamingBuffer:
    """Accumulates LLM tokens and separates UI-visible text from control tags."""

    _TAG_PREFIXES = ("<tool_call", "<task_complete")

    def __init__(self) -> None:
        self._buf = ""
        self._in_fence = False
        self._full = ""  # complete accumulated response
        self._fence_carry = ""  # incomplete line for incremental ``` fence detection

    def feed(self, token: str) -> List[str]:
        """Feed a token; return list of text chunks safe to send to the UI."""
        self._full += token
        self._buf += token
        self._advance_fence_state(token)
        if self._in_fence:
            return self._flush_all()

        for prefix in self._TAG_PREFIXES:
            if prefix in self._buf:
                if self._has_complete_tag():
                    return self._flush_before_tag()
                return []  # hold — tag may still be forming
            for plen in range(1, len(prefix)):
                if self._buf.endswith(prefix[:plen]):
                    safe = self._buf[: -plen]
                    self._buf = self._buf[-plen:]
                    return [safe] if safe else []

        return self._flush_all()

    def _advance_fence_state(self, token: str) -> None:
        """Toggle _in_fence only on complete lines ending with \\n (avoids re-scanning the whole buffer)."""
        combined = self._fence_carry + token
        parts = combined.split("\n")
        self._fence_carry = parts.pop()
        for line in parts:
            stripped = line.strip()
            if stripped.startswith("```"):
                self._in_fence = not self._in_fence

    @property
    def full_response(self) -> str:
        return self._full

    def end_stream(self) -> None:
        """Apply fence toggles for a trailing partial line (no final newline)."""
        if self._fence_carry:
            stripped = self._fence_carry.strip()
            if stripped.startswith("```"):
                self._in_fence = not self._in_fence
            self._fence_carry = ""

    def flush_remaining(self) -> str:
        """Return any buffered text at end of stream."""
        text = self._buf
        self._buf = ""
        return text

    def _has_complete_tag(self) -> bool:
        return ("</tool_call>" in self._buf) or ("</task_complete>" in self._buf)

    def _flush_all(self) -> List[str]:
        text = self._buf
        self._buf = ""
        return [text] if text else []

    def _flush_before_tag(self) -> List[str]:
        for tag_open in ("<tool_call>", "<task_complete>"):
            idx = self._buf.find(tag_open)
            if idx >= 0:
                safe = self._buf[:idx]
                self._buf = self._buf[idx:]
                return [safe] if safe else []
        return []


# ---------------------------------------------------------------------------
# agent_llm_stream — unified async token generator for all providers
# ---------------------------------------------------------------------------

def _agent_message_has_tool_meta(msg: Dict[str, Any]) -> bool:
    return any(
        k.startswith("_")
        for k in msg
        if k not in ("role", "content")
    )


def _merge_consecutive_roles_for_agent(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Merge consecutive same-role messages when both are plain (no _tool_call metadata)."""
    if not messages:
        return messages
    merged: List[Dict[str, Any]] = [dict(messages[0])]
    for msg in messages[1:]:
        prev = merged[-1]
        if (
            msg.get("role") == prev.get("role")
            and not _agent_message_has_tool_meta(msg)
            and not _agent_message_has_tool_meta(prev)
        ):
            prev["content"] = (prev.get("content") or "") + "\n---\n" + (msg.get("content") or "")
        else:
            merged.append(dict(msg))
    return merged


def _ollama_agent_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Strip internal keys; Ollama only sees role + content."""
    return [
        {"role": m["role"], "content": m.get("content", "")}
        for m in messages
        if m.get("role") in ("system", "user", "assistant")
    ]


def _strip_tool_result_prefix(user_content: str) -> str:
    if user_content.startswith("[Tool Result:"):
        idx = user_content.find("]\n")
        if idx >= 0:
            return user_content[idx + 2 :]
    return user_content


def _anthropic_api_messages(nonsys: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for m in nonsys:
        role = m.get("role")
        if role == "assistant" and "_tool_call" in m:
            tc = m["_tool_call"]
            blocks: List[Dict[str, Any]] = []
            txt = (m.get("content") or "").strip()
            if txt:
                blocks.append({"type": "text", "text": txt})
            inp = tc.get("input")
            if not isinstance(inp, dict):
                inp = {}
            blocks.append(
                {
                    "type": "tool_use",
                    "id": tc["id"],
                    "name": tc["name"],
                    "input": inp,
                }
            )
            out.append({"role": "assistant", "content": blocks})
            continue
        if role == "user" and m.get("_tool_call_id"):
            body = _strip_tool_result_prefix(m.get("content", ""))
            tr: Dict[str, Any] = {
                "type": "tool_result",
                "tool_use_id": m["_tool_call_id"],
                "content": body,
            }
            if m.get("_tool_is_error"):
                tr["is_error"] = True
            out.append({"role": "user", "content": [tr]})
            continue
        out.append({"role": role, "content": m.get("content", "")})
    return out


def _deepseek_api_messages(msgs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for m in msgs:
        role = m.get("role")
        if role == "assistant" and m.get("_tool_calls_openai"):
            entry = {
                "role": "assistant",
                "content": (m.get("content") or "").strip() or "",
                "tool_calls": m["_tool_calls_openai"],
            }
            out.append(entry)
            continue
        if role == "user" and m.get("_tool_call_id"):
            body = _strip_tool_result_prefix(m.get("content", ""))
            out.append(
                {
                    "role": "tool",
                    "tool_call_id": m["_tool_call_id"],
                    "content": body,
                }
            )
            continue
        out.append({"role": role, "content": m.get("content", "")})
    return out


def _iter_agent_ollama(messages: List[Dict[str, Any]], model: str) -> Any:
    if query_mod is None or not getattr(query_mod, "OLLAMA_LIB_AVAILABLE", False):
        yield "Error: Ollama is not available."
        return
    om = getattr(query_mod, "_ollama_mod", None)
    if om is None:
        yield "Error: Ollama module not loaded."
        return
    clean = _ollama_agent_messages(messages)
    try:
        stream = om.chat(model=model, messages=clean, stream=True)
    except Exception as exc:
        log.warning("agent ollama.chat failed: %s", exc)
        yield f"Error: Ollama call failed: {exc}"
        return
    for chunk in stream:
        tok = query_mod._stream_chunk_text(chunk)
        if tok:
            yield tok


def _iter_agent_anthropic(messages: List[Dict[str, Any]], model: str, api_key: str) -> Any:
    if not ANTHROPIC_AVAILABLE or anthropic is None:
        yield "Error: install anthropic (pip install anthropic)."
        return
    merged = _merge_consecutive_roles_for_agent(messages)
    system_content = ""
    non_system: List[Dict[str, Any]] = []
    for m in merged:
        if m.get("role") == "system":
            c = m.get("content") or ""
            system_content += ("\n" + c) if system_content else c
        else:
            non_system.append(m)
    if not non_system or non_system[0].get("role") != "user":
        non_system.insert(0, {"role": "user", "content": "(continue)"})
    api_messages = _anthropic_api_messages(non_system)
    text_parts: List[str] = []
    try:
        with anthropic.Anthropic(api_key=api_key).messages.stream(
            model=model or "claude-3-5-haiku-20241022",
            max_tokens=8192,
            system=system_content,
            messages=api_messages,
            tools=_anthropic_tool_schemas(),
            tool_choice={"type": "auto"},
        ) as stream:
            for text in stream.text_stream:
                text_parts.append(text)
                yield text
            final = stream.get_final_message()
    except Exception as exc:
        log.warning("agent anthropic stream failed: %s", exc)
        yield f"Error: Anthropic call failed: {exc}"
        return

    if getattr(final, "stop_reason", None) == "tool_use" and final.content:
        for block in final.content:
            if getattr(block, "type", None) == "tool_use":
                raw_in = getattr(block, "input", None)
                kwargs: Dict[str, Any] = raw_in if isinstance(raw_in, dict) else {}
                yield _NativeToolCall(
                    name=getattr(block, "name", "") or "",
                    kwargs=kwargs,
                    tool_call_id=getattr(block, "id", "") or "",
                    text_before="".join(text_parts),
                )
                return


def _iter_agent_deepseek(messages: List[Dict[str, Any]], model: str, api_key: str) -> Any:
    if not OPENAI_SDK_AVAILABLE or OpenAI is None:
        yield "Error: install openai (pip install openai)."
        return
    merged = _merge_consecutive_roles_for_agent(messages)
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    api_messages = _deepseek_api_messages(merged)
    text_parts: List[str] = []
    tc_accum: Dict[int, Dict[str, str]] = {}
    try:
        stream = client.chat.completions.create(
            model=model or "deepseek-chat",
            messages=api_messages,
            tools=_agent_tools_openai_style(),
            tool_choice="auto",
            stream=True,
        )
        for chunk in stream:
            choice = chunk.choices[0] if chunk.choices else None
            if choice is None:
                continue
            delta = choice.delta
            if delta is None:
                continue
            c = getattr(delta, "content", None)
            if c:
                text_parts.append(c)
                yield c
            tcs = getattr(delta, "tool_calls", None)
            if not tcs:
                continue
            for tc in tcs:
                idx = int(getattr(tc, "index", 0) or 0)
                if idx not in tc_accum:
                    tc_accum[idx] = {"id": "", "name": "", "arguments": ""}
                tid = getattr(tc, "id", None)
                if tid:
                    tc_accum[idx]["id"] = (tc_accum[idx]["id"] or "") + tid
                fn = getattr(tc, "function", None)
                if fn is not None:
                    n = getattr(fn, "name", None)
                    if n:
                        tc_accum[idx]["name"] += n
                    a = getattr(fn, "arguments", None)
                    if a:
                        tc_accum[idx]["arguments"] += a
    except Exception as exc:
        log.warning("agent deepseek stream failed: %s", exc)
        yield f"Error: DeepSeek call failed: {exc}"
        return

    if not tc_accum:
        return
    first_idx = min(tc_accum.keys())
    first = tc_accum[first_idx]
    raw_args = first.get("arguments") or "{}"
    try:
        kwargs = json.loads(raw_args)
        if not isinstance(kwargs, dict):
            kwargs = {}
    except json.JSONDecodeError:
        log.warning("DeepSeek tool arguments JSON decode failed: %s", raw_args[:200])
        kwargs = {}
    yield _NativeToolCall(
        name=first.get("name", "") or "",
        kwargs=kwargs,
        tool_call_id=first.get("id", "") or "",
        text_before="".join(text_parts),
    )


async def agent_llm_stream(
    messages: List[Dict[str, Any]],
    provider: str,
    model: str,
    api_key: str,
) -> AsyncIterator[Union[str, _NativeToolCall]]:
    """Unified async generator: text tokens and optional trailing native tool call."""
    if provider == "anthropic":
        factory = lambda: _iter_agent_anthropic(messages, model, api_key)
    elif provider == "deepseek":
        factory = lambda: _iter_agent_deepseek(messages, model, api_key)
    else:
        factory = lambda: _iter_agent_ollama(messages, model)

    it = iter(factory())

    def _next() -> Any:
        try:
            return next(it)
        except StopIteration:
            return _SENTINEL

    while True:
        item = await asyncio.to_thread(_next)
        if item is _SENTINEL:
            break
        if isinstance(item, _NativeToolCall):
            yield item
        else:
            yield str(item)


# ---------------------------------------------------------------------------
# Context window management
# ---------------------------------------------------------------------------

def _truncate_old_messages(messages: List[Dict[str, Any]], ctx_limit: int) -> None:
    """Truncate older tool results when estimated context exceeds ~80% of limit; keep last 3 tool results full."""
    total_chars = sum(len(m["content"]) for m in messages)
    est_tokens = total_chars / 3.5
    if est_tokens < ctx_limit * 0.8:
        return
    tool_idxs = [
        i
        for i, m in enumerate(messages)
        if m["role"] == "user" and m["content"].startswith("[Tool Result:")
    ]
    if len(tool_idxs) <= 3:
        return
    keep = set(tool_idxs[-3:])
    for i in tool_idxs:
        if i in keep:
            continue
        m = messages[i]
        orig_len = len(m["content"])
        if orig_len > 200:
            m["content"] = (
                m["content"][:120] + f"\n... [Truncated tool result, was {orig_len} chars]"
            )


# ---------------------------------------------------------------------------
# Tool call parsing
# ---------------------------------------------------------------------------

_TOOL_CALL_RE = re.compile(r"<tool_call>(.*?)</tool_call>", re.DOTALL)
_TASK_DONE_RE = re.compile(r"<task_complete>(.*?)</task_complete>", re.DOTALL)
_MD_FENCE_RE = re.compile(r"```(?:json|JSON)?\s*\n?(.*?)\n?\s*```", re.DOTALL)


def _strip_md_fences(raw: str) -> str:
    """Strip markdown code fences that LLMs (qwen2.5, etc.) wrap around tool JSON."""
    stripped = raw.strip()
    m = _MD_FENCE_RE.search(stripped)
    if m:
        return m.group(1).strip()
    return stripped


def _parse_tool_call(text: str) -> Optional[Dict[str, Any]]:
    """Extract the first tool_call JSON from the response text."""
    m = _TOOL_CALL_RE.search(text)
    if not m:
        return None
    inner = _strip_md_fences(m.group(1))
    try:
        return json.loads(inner)
    except json.JSONDecodeError as exc:
        return {"_parse_error": str(exc), "_raw": inner[:300]}


def _parse_task_complete(text: str) -> Optional[str]:
    m = _TASK_DONE_RE.search(text)
    return m.group(1).strip() if m else None


# ---------------------------------------------------------------------------
# Tool dispatch helper
# ---------------------------------------------------------------------------

_TOOLS_NEEDING_QUERY_MOD = {"search_codebase"}


def _dispatch_tool(
    tool_data: Dict[str, Any],
    session: AgentSession,
    query_module: Any,
) -> Tuple[str, ToolResult]:
    """Validate and execute a tool call, returning (tool_name, result)."""
    if "_parse_error" in tool_data:
        return "unknown", ToolResult(
            success=False, output="",
            error=f"Malformed tool call JSON: {tool_data['_parse_error']}. Raw: {tool_data.get('_raw', '')[:200]}",
        )

    name = tool_data.get("name", "")
    kwargs = tool_data.get("kwargs", {})
    if not isinstance(kwargs, dict):
        kwargs = {}

    if name not in TOOL_REGISTRY:
        return name, ToolResult(
            success=False, output="",
            error=f"Unknown tool: {name!r}. Available: {', '.join(TOOL_REGISTRY.keys())}",
        )

    kwargs.pop("session", None)
    kwargs.pop("query_mod", None)

    if name in _TOOLS_NEEDING_QUERY_MOD:
        return name, TOOL_REGISTRY[name](session=session, query_mod=query_module, **kwargs)
    return name, TOOL_REGISTRY[name](session=session, **kwargs)


# ---------------------------------------------------------------------------
# execute_agent_step — one iteration of the ReAct loop (provider-agnostic)
# ---------------------------------------------------------------------------

_STEP_TOOL = "tool"
_STEP_COMPLETE = "complete"
_STEP_TEXT = "text"
_STEP_ERROR = "error"


async def execute_agent_step(
    messages: List[Dict[str, Any]],
    provider: str,
    model: str,
    api_key: str,
    session: AgentSession,
    query_module: Any,
    iteration: int,
) -> AsyncIterator[Dict[str, Any]]:
    """Execute one ReAct step: stream LLM, parse response, dispatch tool if needed.

    Yields dicts with ``type`` key:
      - ``token``       – partial text for the UI
      - ``agent_action`` – tool call about to execute
      - ``tool_result``  – tool execution output
      - ``step_result``  – final summary of the step (always last yield)
    The caller inspects the ``step_result`` event to decide whether to continue,
    complete, or rollback.
    """
    buf = StreamingBuffer()
    native: Optional[_NativeToolCall] = None
    try:
        async for item in agent_llm_stream(messages, provider, model, api_key):
            if isinstance(item, _NativeToolCall):
                native = item
                continue
            for segment in buf.feed(item):
                if segment:
                    yield {"type": "token", "text": segment}
    except Exception as exc:
        log.exception("Agent LLM stream error in execute_agent_step")
        yield {"type": "step_result", "kind": _STEP_ERROR, "error": str(exc)}
        return

    buf.end_stream()
    remaining = buf.flush_remaining()
    if remaining and not remaining.lstrip().startswith("<"):
        yield {"type": "token", "text": remaining}

    full_response = buf.full_response

    if native is not None:
        tool_data: Dict[str, Any] = {"name": native.name, "kwargs": native.kwargs}
        tool_name = tool_data.get("name", "unknown")
        tool_kwargs = tool_data.get("kwargs", {})
        target_hint = (
            tool_kwargs.get("filepath")
            or tool_kwargs.get("title", "")[:60]
            or tool_kwargs.get("command", "")[:60]
            or tool_kwargs.get("query", "")[:60]
            or ""
        ) if isinstance(tool_kwargs, dict) else ""
        if tool_name == "remember_concept" and isinstance(tool_kwargs, dict):
            st = str(tool_kwargs.get("storage", "domain_docs"))[:24]
            target_hint = f"{st}:{target_hint}" if target_hint else st

        yield {"type": "agent_action", "tool": tool_name, "target": target_hint, "iteration": iteration}

        name, result = await asyncio.to_thread(_dispatch_tool, tool_data, session, query_module)

        result_for_sse = result.output[:2000] if result.output else result.error[:2000]
        yield {"type": "tool_result", "tool": name, "success": result.success, "output": result_for_sse}

        yield {
            "type": "step_result",
            "kind": _STEP_TOOL,
            "full_response": full_response,
            "tool_name": name,
            "tool_result": result,
            "native_tool_meta": {
                "tool_call_id": native.tool_call_id,
                "name": native.name,
                "kwargs": native.kwargs,
                "provider": provider,
            },
        }
        return

    summary = _parse_task_complete(full_response)
    if summary is not None:
        yield {"type": "step_result", "kind": _STEP_COMPLETE, "summary": summary, "full_response": full_response}
        return

    tool_data = _parse_tool_call(full_response)
    if tool_data is None:
        yield {"type": "step_result", "kind": _STEP_TEXT, "full_response": full_response}
        return

    tool_name = tool_data.get("name", "unknown")
    tool_kwargs = tool_data.get("kwargs", {})
    target_hint = (
        tool_kwargs.get("filepath")
        or tool_kwargs.get("title", "")[:60]
        or tool_kwargs.get("command", "")[:60]
        or tool_kwargs.get("query", "")[:60]
        or ""
    ) if isinstance(tool_kwargs, dict) else ""
    if tool_name == "remember_concept" and isinstance(tool_kwargs, dict):
        st = str(tool_kwargs.get("storage", "domain_docs"))[:24]
        target_hint = f"{st}:{target_hint}" if target_hint else st

    yield {"type": "agent_action", "tool": tool_name, "target": target_hint, "iteration": iteration}

    name, result = await asyncio.to_thread(_dispatch_tool, tool_data, session, query_module)

    result_for_sse = result.output[:2000] if result.output else result.error[:2000]
    yield {"type": "tool_result", "tool": name, "success": result.success, "output": result_for_sse}

    yield {
        "type": "step_result",
        "kind": _STEP_TOOL,
        "full_response": full_response,
        "tool_name": name,
        "tool_result": result,
    }


# ---------------------------------------------------------------------------
# @ mention parsing (pre-flight context injection)
# ---------------------------------------------------------------------------

_AT_MENTION_RE = re.compile(r"@(web|codebase|docs)\b", re.IGNORECASE)


def parse_at_mentions(text: str) -> Tuple[str, set]:
    """Return (cleaned_text, set_of_lowercase_mentions) from ``@web``, ``@codebase``, ``@docs``."""
    mentions = {m.lower() for m in _AT_MENTION_RE.findall(text)}
    cleaned = _AT_MENTION_RE.sub("", text).strip()
    return cleaned, mentions


async def _preflight_context(
    mentions: set,
    query_text: str,
    session: AgentSession,
    query_module: Any,
) -> str:
    """Run pre-flight retrieval for @mentions, returning markdown context block."""
    from agent_tools import web_search as _ws, search_codebase as _sc
    parts: List[str] = []

    if "web" in mentions:
        wr = await asyncio.to_thread(_ws, session, query_text)
        if wr.success and wr.output:
            parts.append(f"## Web Search Results\n{wr.output}")

    if "docs" in mentions:
        sr = await asyncio.to_thread(
            _sc, session, query_text, query_module, domain="", top_k=5, search_type="domain",
        )
        if sr.success and sr.output and sr.output != "No matching results found.":
            parts.append(f"## Domain Docs Search\n{sr.output}")
    if "codebase" in mentions:
        sr = await asyncio.to_thread(
            _sc, session, query_text, query_module, domain="", top_k=5, search_type="code",
        )
        if sr.success and sr.output and sr.output != "No matching results found.":
            parts.append(f"## Codebase Search Results\n{sr.output}")

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# ReAct SSE stream
# ---------------------------------------------------------------------------

async def agent_sse_stream(body: AgentBody) -> AsyncIterator[str]:
    """Core ReAct loop yielding SSE events."""
    global _agent_busy
    _agent_cancel.clear()

    session_id = uuid4().hex[:12]
    workspace = resolve_agent_workspace(body.workspace)
    if not workspace.is_dir():
        yield f"data: {json.dumps({'type': 'agent_state', 'status': 'failed', 'reason': f'Workspace not found: {workspace}'})}\n\n"
        return

    db_path = resolve_db_path(form_path=body.db_path)
    chroma_client = None
    chroma_embedder = None
    try:
        chroma_client, chroma_embedder, cmap, _ = await ensure_chroma(db_path)
    except Exception:
        cmap = {}

    session = AgentSession(
        session_id=session_id,
        workspace_root=workspace,
        cmap=cmap,
        db_path=db_path,
        chroma_client=chroma_client,
        chroma_embedder=chroma_embedder,
    )

    max_iter = min(body.max_iterations, 25)

    cleaned_task, mentions = parse_at_mentions(body.task)
    task_content = cleaned_task or body.task

    if mentions:
        yield f"data: {json.dumps({'type': 'agent_state', 'status': 'gathering_context', 'mentions': sorted(mentions)})}\n\n"
        try:
            ctx = await _preflight_context(mentions, cleaned_task, session, query_mod)
            if ctx:
                task_content = f"{cleaned_task}\n\n---\n## Pre-fetched Context\n{ctx}"
        except Exception as exc:
            log.warning("Pre-flight @mention context failed: %s", exc)

    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": build_agent_system_prompt(body.llm_provider)},
        {"role": "user", "content": task_content},
    ]

    yield f"data: {json.dumps({'type': 'agent_state', 'status': 'planning', 'session_id': session_id})}\n\n"

    try:
        for iteration in range(1, max_iter + 1):
            if _agent_cancel.is_set():
                rolled = session.rollback()
                yield f"data: {json.dumps({'type': 'agent_state', 'status': 'cancelled', 'rolled_back': rolled})}\n\n"
                return

            _truncate_old_messages(messages, _AGENT_CTX_LIMIT)

            yield f"data: {json.dumps({'type': 'agent_state', 'status': 'thinking', 'iteration': iteration, 'max': max_iter})}\n\n"

            step_result = None
            async for event in execute_agent_step(
                messages, body.llm_provider, body.llm_model, body.api_key,
                session, query_mod, iteration,
            ):
                if event["type"] == "step_result":
                    step_result = event
                else:
                    yield f"data: {json.dumps(event)}\n\n"
                    if (
                        event.get("type") == "tool_result"
                        and event.get("tool") == "remember_concept"
                        and event.get("success")
                    ):
                        yield f"data: {json.dumps({'type': 'agent_status', 'status': 'memory_saved', 'message': 'Agent saved new knowledge to RAG Database'})}\n\n"

            if step_result is None:
                continue

            kind = step_result["kind"]

            if kind == _STEP_ERROR:
                rolled = session.rollback()
                err_msg = step_result.get("error", "unknown")
                yield f"data: {json.dumps({'type': 'error', 'message': 'LLM error: ' + err_msg})}\n\n"
                yield f"data: {json.dumps({'type': 'agent_state', 'status': 'failed', 'reason': 'LLM error: ' + err_msg, 'rolled_back': rolled})}\n\n"
                return

            if kind == _STEP_COMPLETE:
                session.cleanup()
                yield f"data: {json.dumps({'type': 'agent_state', 'status': 'complete', 'summary': step_result['summary']})}\n\n"
                return

            if kind == _STEP_TOOL:
                if _agent_cancel.is_set():
                    rolled = session.rollback()
                    yield f"data: {json.dumps({'type': 'agent_state', 'status': 'cancelled', 'rolled_back': rolled})}\n\n"
                    return
                tr = step_result["tool_result"]
                tool_output = tr.output if tr.success else (tr.error or tr.output)
                ntm = step_result.get("native_tool_meta")
                prov = body.llm_provider
                if ntm and prov == "anthropic":
                    messages.append(
                        {
                            "role": "assistant",
                            "content": step_result["full_response"],
                            "_tool_call": {
                                "id": ntm["tool_call_id"],
                                "name": ntm["name"],
                                "input": ntm["kwargs"],
                            },
                        }
                    )
                    messages.append(
                        {
                            "role": "user",
                            "content": f"[Tool Result: {step_result['tool_name']}]\n{tool_output}",
                            "_tool_call_id": ntm["tool_call_id"],
                            "_tool_is_error": not tr.success,
                        }
                    )
                elif ntm and prov == "deepseek":
                    messages.append(
                        {
                            "role": "assistant",
                            "content": step_result["full_response"],
                            "_tool_calls_openai": [
                                {
                                    "id": ntm["tool_call_id"],
                                    "type": "function",
                                    "function": {
                                        "name": ntm["name"],
                                        "arguments": json.dumps(ntm["kwargs"]),
                                    },
                                }
                            ],
                        }
                    )
                    messages.append(
                        {
                            "role": "user",
                            "content": f"[Tool Result: {step_result['tool_name']}]\n{tool_output}",
                            "_tool_call_id": ntm["tool_call_id"],
                        }
                    )
                else:
                    messages.append({"role": "assistant", "content": step_result["full_response"]})
                    messages.append(
                        {
                            "role": "user",
                            "content": f"[Tool Result: {step_result['tool_name']}]\n{tool_output}",
                        }
                    )
                continue

            messages.append({"role": "assistant", "content": step_result.get("full_response", "")})

        rolled = session.rollback()
        yield f"data: {json.dumps({'type': 'agent_state', 'status': 'failed', 'reason': f'Max iterations ({max_iter}) reached. All file changes rolled back.', 'rolled_back': rolled})}\n\n"

    except Exception as exc:
        log.exception("Agent loop unhandled error")
        try:
            rolled = session.rollback()
        except Exception:
            rolled = []
        yield f"data: {json.dumps({'type': 'agent_state', 'status': 'failed', 'reason': f'Unhandled error: {exc}', 'rolled_back': rolled})}\n\n"


# ---------------------------------------------------------------------------
# Agent endpoints
# ---------------------------------------------------------------------------

@app.get("/api/agent/tool-schemas")
async def api_agent_tool_schemas() -> JSONResponse:
    """OpenAI-compatible tool definitions; shell tool omitted when RAG_AGENT_ALLOW_SHELL disables it."""
    tools = _agent_tools_openai_style()
    return JSONResponse(
        jsonable_encoder(
            {
                "tools": tools,
                "note": (
                    "Ollama dashboard agent uses <tool_call> XML in the ReAct loop; "
                    "Anthropic and DeepSeek use native tools with the same schemas."
                ),
            }
        )
    )


@app.post("/api/agent")
async def api_agent(body: AgentBody) -> StreamingResponse:
    global _agent_busy
    _reject_query_while_ingesting()

    if body.llm_provider == "anthropic":
        if not ANTHROPIC_AVAILABLE:
            raise HTTPException(
                status_code=503,
                detail="To use Claude with the agent, install: pip install anthropic",
            )
        if not (body.api_key or "").strip():
            raise HTTPException(
                status_code=400,
                detail="Enter your Anthropic API key for the agent, or switch to Local Ollama.",
            )
    elif body.llm_provider == "deepseek":
        if not OPENAI_SDK_AVAILABLE:
            raise HTTPException(
                status_code=503,
                detail="To use DeepSeek with the agent, install: pip install openai",
            )
        if not (body.api_key or "").strip():
            raise HTTPException(
                status_code=400,
                detail="Enter your DeepSeek API key for the agent, or switch to Local Ollama.",
            )
    elif body.llm_provider == "ollama":
        if query_mod is None:
            raise HTTPException(
                status_code=503,
                detail="query.py is unavailable; the agent cannot run.",
            )
        if not getattr(query_mod, "OLLAMA_LIB_AVAILABLE", False):
            raise HTTPException(
                status_code=503,
                detail="Install the ollama Python package (pip install ollama) for Local Ollama agent runs.",
            )
        ollama_ok = await asyncio.to_thread(query_mod.check_ollama)
        if not ollama_ok:
            raise HTTPException(
                status_code=503,
                detail="Ollama is not reachable at http://127.0.0.1:11434 — start Ollama before running the agent.",
            )

    if body.workspace.strip():
        raw_ws = Path(body.workspace.strip()).expanduser()
        if not raw_ws.is_absolute():
            raise HTTPException(
                status_code=400,
                detail="Agent workspace override must be an absolute path on the server (e.g. /home/you/project).",
            )
    ws = resolve_agent_workspace(body.workspace)
    if not ws.is_dir():
        raise HTTPException(
            status_code=400,
            detail=f"Agent workspace is not a directory: {ws}",
        )

    if not _agent_slot.acquire(blocking=False):
        raise HTTPException(
            status_code=409,
            detail="An agent session is already running. Wait for it to finish or cancel it.",
        )
    _agent_busy = True
    _agent_cancel.clear()

    async def _guarded_stream() -> AsyncIterator[str]:
        global _agent_busy
        try:
            async for event in agent_sse_stream(body):
                yield event
        finally:
            _agent_busy = False
            _agent_cancel.clear()
            _agent_slot.release()

    return StreamingResponse(_guarded_stream(), media_type="text/event-stream")


@app.post("/api/agent/cancel")
async def api_agent_cancel() -> Dict[str, str]:
    if not _agent_busy:
        return {"detail": "No active agent session"}
    _agent_cancel.set()
    return {"detail": "Cancel signal sent"}
