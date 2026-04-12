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
  GET /api/chunks/list — Paged Chunk Inspector catalog (?offset=&page_limit=; global order by collection name then Chroma offset).

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

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field, field_validator

# Repo root = directory containing this file (ingest.py, query.py, hybrid_search.py live here).
# When this file lives under Studio-Portable-RAG (bundled Ollama + venv), defaults use this folder
# for VectorDB/Codebase instead of repo/Studio-Portable-RAG/...
REPO_ROOT = Path(__file__).resolve().parent

log = logging.getLogger("gui_backend")


def _is_portable_bundle_root(repo: Path) -> bool:
    """True if `repo` looks like a Studio-Portable-RAG build (Ollama + venv + ingest)."""
    if not repo.is_dir():
        return False
    if not (repo / "ingest.py").is_file():
        return False
    if not (repo / "Ollama").is_dir() or not (repo / "Python").is_dir():
        return False
    return True


def _mode_to_default_source_subdir(mode: str) -> str:
    """Same folder mapping as run.sh when SOURCE_FOLDER is unset."""
    m = (mode or "").strip()
    if m in ("domain", "theory"):
        return "DomainDocs"
    if m == "rfc":
        return "RFCs"
    if m == "mib":
        return "MIBs"
    if m in ("community", "customer"):
        return "CommunityData"
    if m in ("code", "release-notes"):
        return "Codebase"
    return "Codebase"


def _dir_has_any_file(path: Path) -> bool:
    """True if *path* is a directory tree that contains at least one file."""
    try:
        for _dp, _dn, filenames in os.walk(path, followlinks=False):
            if filenames:
                return True
    except OSError:
        return False
    return False


def _default_ingest_source_dir(mode: Optional[str]) -> Optional[Path]:
    """Resolve default --source: prefer a directory that actually contains files.

    When the dashboard runs from ``Studio-Portable-RAG/``, the bundled ``Codebase/``
    folder is often empty while the real clone lives next to it at
    ``<repo>/Codebase/`` (e.g. ``Codebase/ngspice``). In that case we pick the parent
    tree if it has files and the portable folder does not.
    """
    if not mode or mode in ("status", "rally", "wiki"):
        return None
    sub = _mode_to_default_source_subdir(mode)
    candidates: List[Path] = []
    if _is_portable_bundle_root(REPO_ROOT):
        candidates.append((REPO_ROOT / sub).resolve())
        candidates.append((REPO_ROOT.parent / sub).resolve())
    else:
        candidates.append((REPO_ROOT / "Studio-Portable-RAG" / sub).resolve())
        candidates.append((REPO_ROOT / sub).resolve())
    first_existing: Optional[Path] = None
    for p in candidates:
        if not p.is_dir():
            continue
        if first_existing is None:
            first_existing = p
        if _dir_has_any_file(p):
            return p
    return first_existing


def _argv_get_source(argv: List[str]) -> Optional[str]:
    for i, a in enumerate(argv):
        if a == "--source" and i + 1 < len(argv):
            return argv[i + 1]
    return None


def _argv_get_val(argv: List[str], flag: str) -> Optional[str]:
    for i, a in enumerate(argv):
        if a == flag and i + 1 < len(argv):
            return argv[i + 1]
    return None


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


def _chroma_persistent_client_for_gui(db_path: str) -> Any:
    """Open Chroma with the same settings as ``query._persistent_chroma_client``.

    Chroma keeps a process-wide singleton per persist path; mixing default settings with
    ``Settings(anonymized_telemetry=False)`` raises: "An instance of Chroma already exists ...".
    """
    if query_mod is not None:
        return query_mod._persistent_chroma_client(db_path)
    import chromadb as _cd

    try:
        from chromadb.config import Settings

        return _cd.PersistentClient(path=db_path, settings=Settings(anonymized_telemetry=False))
    except Exception:
        return _cd.PersistentClient(path=db_path)


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
    if _is_portable_bundle_root(REPO_ROOT):
        d = (REPO_ROOT / "VectorDB").resolve()
    else:
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
    if _is_portable_bundle_root(REPO_ROOT):
        candidates = (REPO_ROOT / "Codebase",)
    else:
        candidates = (
            REPO_ROOT / "Studio-Portable-RAG" / "Codebase",
            REPO_ROOT / "Codebase",
        )
    for candidate in candidates:
        if candidate.is_dir():
            return candidate.resolve()
    fallback = (REPO_ROOT / "Codebase").resolve()
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def chunk_explorer_default_source_base() -> str:
    """Default Chunk Inspector source root: Codebase/ngspice when present, else Codebase."""
    root = resolved_source_base()
    ng = root / "ngspice"
    if ng.is_dir():
        return str(ng.resolve())
    return str(root.resolve())


# Chroma/SQLite fails ``get(limit=N)`` for large N (e.g. ``too many SQL variables``); page gets.
_CHROMA_CATALOG_PAGE = 200


def _chroma_catalog_counts_and_order(client: Any) -> Tuple[List[str], Dict[str, int], int]:
    """Collection names (sorted), per-collection counts, and total chunk count."""
    names: List[str] = []
    counts: Dict[str, int] = {}
    total = 0
    for info in sorted(client.list_collections(), key=lambda x: x.name):
        names.append(info.name)
        coll = client.get_collection(info.name)
        try:
            n = int(coll.count())
        except Exception:
            n = -1
        counts[info.name] = n
        if n > 0:
            total += n
    return names, counts, total


def _list_chroma_catalog_page(
    db_path: str,
    source_base: Optional[str],
    start_offset: int,
    max_rows: int,
) -> Dict[str, Any]:
    """Return one page of flat catalog rows (global order: sorted collection name, then Chroma offset).

    ``start_offset`` skips that many chunks across the union of collections in that order.
    """
    client = _chroma_persistent_client_for_gui(db_path)
    rel_root: Optional[Path] = None
    if source_base and str(source_base).strip():
        p = Path(str(source_base).strip()).expanduser().resolve()
        if p.is_dir():
            rel_root = p
    if rel_root is None:
        rel_root = resolved_source_base()
    rel_root = rel_root.resolve()

    errors: List[str] = []
    names, counts, total_in_db = _chroma_catalog_counts_and_order(client)
    skip = max(0, int(start_offset))
    rows: List[Dict[str, Any]] = []

    if skip >= total_in_db > 0 or total_in_db == 0:
        return {
            "chunks": [],
            "offset": int(start_offset),
            "next_offset": total_in_db,
            "returned_this_page": 0,
            "total_in_db": total_in_db,
            "has_more": False,
            "collections_order": names,
            "collection_counts": counts,
            "scan_errors": errors,
        }

    for coll_name in names:
        if len(rows) >= max_rows:
            break
        cnt = counts.get(coll_name, -1)
        if cnt <= 0:
            continue
        if skip >= cnt:
            skip -= cnt
            continue
        coll = client.get_collection(coll_name)
        co = skip
        skip = 0
        try:
            while len(rows) < max_rows and co < cnt:
                take = min(_CHROMA_CATALOG_PAGE, max_rows - len(rows), cnt - co)
                if take <= 0:
                    break
                batch = coll.get(
                    include=["metadatas", "documents"],
                    limit=take,
                    offset=co,
                )
                ids_ = batch.get("ids") or []
                if not ids_:
                    break
                docs = batch.get("documents") or []
                metas = batch.get("metadatas") or []
                for i, cid in enumerate(ids_):
                    if len(rows) >= max_rows:
                        break
                    meta = metas[i] if i < len(metas) else None
                    if not isinstance(meta, dict):
                        meta = {}
                    doc = docs[i] if i < len(docs) else ""
                    if not isinstance(doc, str):
                        doc = str(doc or "")
                    abs_src = str(meta.get("source") or "").strip()
                    rel_path = ""
                    if abs_src:
                        try:
                            rel_path = str(Path(abs_src).resolve().relative_to(rel_root)).replace(
                                "\\", "/"
                            )
                        except ValueError:
                            rel_path = ""
                    preview = doc[:500] if len(doc) > 500 else doc
                    rows.append(
                        {
                            "chunk_id": cid,
                            "collection": coll_name,
                            "text": preview,
                            "text_truncated": len(doc) > 500,
                            "metadata": jsonable_encoder(meta),
                            "abs_source": abs_src,
                            "rel_path": rel_path,
                        }
                    )
                co += len(ids_)
                if len(ids_) < take:
                    break
        except Exception as exc:
            msg = f"{coll_name}: get failed: {exc!s}"
            errors.append(msg)
            log.warning("chunks/list %s", msg)
            continue

    next_off = int(start_offset) + len(rows)
    if total_in_db <= 0 or len(rows) == 0:
        has_more = False
    else:
        has_more = next_off < total_in_db

    return {
        "chunks": rows,
        "offset": int(start_offset),
        "next_offset": next_off,
        "returned_this_page": len(rows),
        "total_in_db": total_in_db,
        "has_more": has_more,
        "collections_order": names,
        "collection_counts": counts,
        "scan_errors": errors,
    }


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


def _embedding_model_inferred_from_db(db_path: str) -> Optional[str]:
    """Model implied by ingestion_config.json / embedding dims when the DB has at least one collection.

    Note: ``query_mod.detect_embedding_model`` prefers ``EMBEDDING_MODEL`` env first, so it must not
    be used here when we need true on-disk inference for Chroma queries.
    """
    if query_mod is None:
        return None
    try:
        client = _chroma_persistent_client_for_gui(db_path)
        if not client.list_collections():
            return None
    except Exception:
        return None
    try:
        inferred = query_mod.embedding_model_from_db_path(db_path)
        return (inferred or "").strip() or None
    except Exception:
        return None


def _embedding_model_for_chroma(db_path: str) -> str:
    """Embedding model for ``connect_chroma_with_retry``: DB-inferred when indexed, else env default."""
    env_model = os.environ.get("EMBEDDING_MODEL", "").strip()
    inferred = _embedding_model_inferred_from_db(db_path)
    if inferred:
        return inferred
    return env_model or "mxbai-embed-large"


async def ensure_chroma(db_path: str) -> Tuple[Any, Any, Dict[str, Any], str]:
    if query_mod is None:
        raise HTTPException(status_code=503, detail="query.py unavailable")

    async with _chroma_lock:
        model_env = await asyncio.to_thread(_embedding_model_for_chroma, db_path)
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
    embedding_model: Optional[str] = None
    embed_workers: Optional[int] = Field(default=None, ge=1, le=64)
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
    enrich_metadata: bool = False
    enrich_model: Optional[str] = None
    enrich_timeout: Optional[float] = Field(default=None, ge=1.0, le=600.0)


def build_ingest_argv(body: IngestBody) -> List[str]:
    script = REPO_ROOT / "ingest.py"
    if not script.is_file():
        raise HTTPException(status_code=500, detail="ingest.py not found next to gui_backend.py")
    args: List[str] = [str(script)]
    if body.mode:
        args += ["--mode", body.mode]
    if body.domain:
        args += ["--domain", body.domain]
    if body.collection:
        args += ["--collection", body.collection]
    db = resolve_db_path(form_path=body.db_path)
    args += ["--db-path", db]
    mode = body.mode
    source_val = (body.source or "").strip() or None
    if mode and mode not in ("status", "rally", "wiki") and not source_val:
        default_src = _default_ingest_source_dir(mode)
        if default_src is not None:
            source_val = str(default_src)
        else:
            sub = _mode_to_default_source_subdir(mode)
            hint = (
                f"{REPO_ROOT / sub}"
                if _is_portable_bundle_root(REPO_ROOT)
                else f"{REPO_ROOT / 'Studio-Portable-RAG' / sub} or {REPO_ROOT / sub}"
            )
            raise HTTPException(
                status_code=400,
                detail=(
                    f"No source path for mode '{mode}' and default folder does not exist yet "
                    f"(expected something like {hint}). Paste a path, use the file browser, "
                    "or create that folder."
                ),
            )
    if source_val and mode and mode != "status":
        args += ["--source", source_val]
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
    if body.enrich_metadata:
        args.append("--enrich-metadata")
        em = (body.enrich_model or "").strip()
        if em:
            args += ["--enrich-model", em]
        if body.enrich_timeout is not None:
            args += ["--enrich-timeout", str(body.enrich_timeout)]
    return args


# -----------------------------------------------------------------------------
# Query API models
# -----------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Per-provider context char budgets and system prompt resolution
# ---------------------------------------------------------------------------

_PROVIDER_CONTEXT_CHARS: Dict[str, int] = {
    "ollama":    120_000,   # ~34k tokens; fits Qwen2.5-coder 32k context safely
    "anthropic": 180_000,   # Claude 3.x 200k context; leave headroom for output
    "deepseek":  110_000,   # deepseek-chat 128k context; leave headroom
}


def _resolve_system_prompt(body: "QueryBody") -> str:
    """Return effective system prompt: explicit > preset > default."""
    if body.system_prompt.strip():
        return body.system_prompt.strip()
    if query_mod is not None:
        preset = (body.system_preset or "").strip().lower()
        if preset:
            return query_mod.DEFAULT_SYSTEM_PROMPTS.get(preset, query_mod.DEFAULT_SYSTEM_PROMPT)
        return query_mod.DEFAULT_SYSTEM_PROMPT
    return (
        "You are an expert ngspice / SPICE circuit simulator and C-codebase assistant. "
        "Answer using ONLY the provided source context. Cite file paths when referencing code."
    )


class QueryBody(BaseModel):
    query: str = Field(..., min_length=1)
    mode: str = "semantic"  # semantic | concept | codebase
    search_type: str = "auto"
    domain: str = ""
    repo: str = ""
    db_path: Optional[str] = None
    top_k: int = Field(5, ge=1, le=QUERY_MAX_K)
    chat: bool = False
    llm_provider: Literal["ollama", "anthropic", "deepseek"] = "ollama"
    llm_model: str = Field(default=DEFAULT_DASHBOARD_LLM)
    api_key: str = Field(default="", description="Anthropic or DeepSeek API key when not using Ollama")
    system_prompt: str = ""
    system_preset: str = Field(
        default="ngspice",
        description="Named system-prompt preset: ngspice | generic | debug | '' to use system_prompt field",
    )
    timeout: int = Field(120, ge=1, le=600)
    history: List[Dict[str, str]] = Field(default_factory=list)
    # Generation controls
    stream_budget: int = Field(
        4096, ge=256, le=16000,
        description="Max output tokens for cloud providers; maps to num_predict for Ollama",
    )
    temperature: float = Field(0.2, ge=0.0, le=2.0)
    top_p: float = Field(0.9, ge=0.0, le=1.0)
    context_budget: int = Field(
        0, ge=0,
        description="Override context char budget (0 = auto per provider)",
    )
    conversation_id: str = Field(default="", description="Opaque ID echoed in the SSE done event")

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
    return query_mod._sync_multi_search_with_dependency_hop(
        qtext, k, effective_type, domain, repo, cmap, db_path
    )


async def run_search(
    body: "QueryBody",
    db_path: str,
    cmap: Dict[str, Any],
    search_query: Optional[str] = None,
) -> List[Any]:
    """Run hybrid/concept search without SIGALRM; retry briefly if SQLite reports locked/busy."""
    qtext = (search_query or body.query).strip()

    # Cloud providers have large context windows — retrieve more candidates
    effective_k = body.top_k
    if body.chat and body.llm_provider in ("anthropic", "deepseek"):
        max_k = query_mod.MAX_K if query_mod is not None else QUERY_MAX_K
        effective_k = min(body.top_k * 3, max_k)

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
                    effective_k,
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
    body: Optional["QueryBody"] = None,
    max_chars: Optional[int] = None,
) -> Any:
    """Sync generator of token strings; empty if ollama missing or error."""
    if query_mod is None or not getattr(query_mod, "OLLAMA_LIB_AVAILABLE", False):
        yield from ()
        return
    om = getattr(query_mod, "_ollama_mod", None)
    if om is None:
        yield from ()
        return
    ctx = query_mod._build_context_blocks(hits, max_chars=max_chars)
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
    # Generation options
    temperature = getattr(body, "temperature", 0.2) if body else 0.2
    top_p = getattr(body, "top_p", 0.9) if body else 0.9
    stream_budget = getattr(body, "stream_budget", 4096) if body else 4096
    options = {
        "temperature": temperature,
        "top_p": top_p,
        "num_ctx": 32768,
        "num_predict": stream_budget,
    }
    try:
        stream = om.chat(model=llm_model, messages=messages, stream=True, options=options)
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
    body: Optional["QueryBody"] = None,
    max_chars: Optional[int] = None,
) -> AsyncIterator[str]:
    it = iter(
        _iter_llm_tokens(
            user_query, hits, llm_model, system_prompt, history_messages, extra_context,
            body=body, max_chars=max_chars,
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
    body: Optional["QueryBody"] = None,
) -> Any:
    if not ANTHROPIC_AVAILABLE or anthropic is None:
        yield "Error: install anthropic (pip install anthropic)."
        return
    client = anthropic.Anthropic(api_key=api_key)
    stream_budget = getattr(body, "stream_budget", 4096) if body else 4096
    temperature = getattr(body, "temperature", 0.2) if body else 0.2
    # Build messages; mark the last user turn for prefix caching
    amsg: List[Dict[str, Any]] = []
    all_msgs = [{"role": m["role"], "content": m["content"]} for m in messages]
    for i, m in enumerate(all_msgs):
        if m["role"] == "user" and i == len(all_msgs) - 1:
            # Cache the large RAG context block on the last user turn
            amsg.append({
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": m["content"],
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
            })
        else:
            amsg.append({"role": m["role"], "content": m["content"]})
    system_blocks: List[Dict[str, Any]] = [
        {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
    ]
    # Extended thinking for claude-3-7-sonnet
    extra_kwargs: Dict[str, Any] = {}
    if "3-7-sonnet" in (model or ""):
        extra_kwargs["thinking"] = {"type": "enabled", "budget_tokens": 8000}
    try:
        with client.messages.stream(
            model=model,
            max_tokens=stream_budget,
            temperature=temperature,
            system=system_blocks,
            messages=amsg,
            **extra_kwargs,
        ) as stream:
            for text in stream.text_stream:
                yield text
    except Exception as exc:
        log.warning("Anthropic stream error: %s", exc)
        yield f"\n\n[Anthropic error: {exc}]"


def _iter_deepseek_text(
    system: str,
    messages: List[Dict[str, str]],
    model: str,
    api_key: str,
    body: Optional["QueryBody"] = None,
) -> Any:
    if not OPENAI_SDK_AVAILABLE or OpenAI is None:
        yield "Error: install openai (pip install openai)."
        return
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    oa: List[Dict[str, Any]] = [{"role": "system", "content": system}]
    oa.extend({"role": m["role"], "content": m["content"]} for m in messages)
    stream_budget = getattr(body, "stream_budget", 4096) if body else 4096
    temperature = getattr(body, "temperature", 0.2) if body else 0.2
    top_p = getattr(body, "top_p", 0.9) if body else 0.9
    eff_model = model or "deepseek-chat"
    is_reasoner = "reasoner" in eff_model.lower()
    # deepseek-reasoner requires temperature=1.0
    eff_temperature = 1.0 if is_reasoner else temperature
    try:
        stream = client.chat.completions.create(
            model=eff_model,
            messages=oa,
            stream=True,
            max_tokens=stream_budget,
            temperature=eff_temperature,
            top_p=top_p,
        )
        _in_think = False
        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta is None:
                continue
            rc = getattr(delta, "reasoning_content", None)
            c = getattr(delta, "content", None)
            if rc:
                if not _in_think:
                    yield "<think>"
                    _in_think = True
                yield rc
            if c:
                if _in_think:
                    yield "</think>\n\n"
                    _in_think = False
                yield c
        if _in_think:
            yield "</think>\n\n"
    except Exception as exc:
        log.warning("DeepSeek stream error: %s", exc)
        yield f"\n\n[DeepSeek error: {exc}]"


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
    body: "QueryBody",
    hits: List[Any],
    extra_context: str = "",
    *,
    user_query_for_llm: Optional[str] = None,
) -> AsyncIterator[str]:
    """Stream answer tokens from Ollama, Claude (Anthropic), or DeepSeek."""
    if query_mod is None:
        return
    user_q = (user_query_for_llm if user_query_for_llm is not None else body.query).strip()

    # Resolve effective system prompt (preset > explicit > default)
    sp = _resolve_system_prompt(body)

    # Resolve per-provider context char budget
    max_chars = (
        body.context_budget
        if body.context_budget and body.context_budget > 0
        else _PROVIDER_CONTEXT_CHARS.get(body.llm_provider, 32_000)
    )

    if body.llm_provider == "ollama":
        async for tok in async_token_stream(
            user_q,
            hits,
            body.llm_model,
            sp,
            body.history or None,
            extra_context or "",
            body=body,
            max_chars=max_chars,
        ):
            yield tok
        return

    # Cloud providers: build context with provider-specific budget
    ctx = await asyncio.to_thread(query_mod._build_context_blocks, hits, max_chars)
    if extra_context:
        ctx = f"{ctx}\n\n## Additional Web Context\n{extra_context}"
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
        _body = body  # capture for lambda closure
        async for tok in _async_from_sync_text_iterator(
            lambda: _iter_anthropic_text(sp, msgs, _body.llm_model, key, body=_body)
        ):
            yield tok
        return

    if body.llm_provider == "deepseek":
        if not key:
            yield "Error: enter your DeepSeek API key in the dashboard, or switch to Local Ollama."
            return
        _body = body
        async for tok in _async_from_sync_text_iterator(
            lambda: _iter_deepseek_text(sp, msgs, _body.llm_model, key, body=_body)
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
    # Embedding model diagnostics (DB-inferred only when collections exist — not env-short-circuited)
    embedding_model_env = os.environ.get("EMBEDDING_MODEL", "").strip() or None
    embedding_model_detected: Optional[str] = None
    try:
        embedding_model_detected = await asyncio.to_thread(
            _embedding_model_inferred_from_db, db_path
        )
    except Exception:
        pass
    model_mismatch = bool(
        embedding_model_env
        and embedding_model_detected
        and embedding_model_env != embedding_model_detected
    )
    source_base = str(resolved_source_base())
    return {
        "db_path": db_path,
        "db_path_source": db_path_source,
        "rag_gui_db_path": env_db or None,
        "source_base": source_base,
        "status": text,
        "ingest_running": ingesting,
        "agent_running": _agent_busy,
        "workspace_root": str(REPO_ROOT),
        "agent_default_workspace": str(resolve_agent_workspace("")),
        "rag_agent_workspace_env": env_ws or None,
        "agent_shell_enabled": is_agent_shell_enabled(),
        "ollama_reachable": ollama_ok,
        "vision_running": _vision_busy,
        "embedding_model_env": embedding_model_env,
        "embedding_model_detected": embedding_model_detected or None,
        "model_mismatch": model_mismatch,
        "chunk_explorer_db_path": str(Path(db_path).resolve()),
        "chunk_explorer_source_default": chunk_explorer_default_source_base(),
    }


def _resolve_browse_root(source_base: Optional[str]) -> Path:
    """Return the browse/chunk root: explicit source_base (validated) or resolved_source_base()."""
    if source_base and source_base.strip():
        p = Path(source_base.strip()).expanduser().resolve()
        if not p.is_dir():
            raise HTTPException(
                status_code=400,
                detail=f"source_base is not an existing directory: {source_base}",
            )
        return p
    return resolved_source_base()


@app.get("/api/browse")
async def api_browse(path: str = "", source_base: Optional[str] = None) -> Dict[str, Any]:
    root = _resolve_browse_root(source_base)
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
async def api_file_raw(path: str, source_base: Optional[str] = None) -> PlainTextResponse:
    """Return raw UTF-8 text for a file under source_base (or RAG_GUI_SOURCE_BASE / default)."""
    if not path.strip():
        raise HTTPException(status_code=400, detail="path query parameter is required")
    root = _resolve_browse_root(source_base)
    target = safe_subpath(root, path)
    if not target.is_file():
        raise HTTPException(status_code=404, detail=f"Not a file: {path}")
    try:
        text = target.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PlainTextResponse(content=text, media_type="text/plain; charset=utf-8")


@app.get("/api/chunks/file")
async def api_chunks_file(
    path: str,
    db_path: Optional[str] = None,
    source_base: Optional[str] = None,
) -> JSONResponse:
    """List all Chroma chunks whose metadata source matches the resolved absolute file path."""
    if not path.strip():
        raise HTTPException(status_code=400, detail="path query parameter is required")
    root = _resolve_browse_root(source_base)
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
                    include=["documents", "metadatas"],
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


@app.get("/api/chunks/list")
async def api_chunks_list(
    db_path: Optional[str] = None,
    source_base: Optional[str] = None,
    offset: int = Query(0, ge=0, le=10_000_000),
    page_limit: int = Query(800, ge=1, le=2000),
) -> JSONResponse:
    """Paged catalog for Chunk Inspector (offset + page_limit for progressive UI loads)."""
    resolved = resolve_db_path(form_path=db_path)
    payload = await asyncio.to_thread(
        _list_chroma_catalog_page,
        resolved,
        source_base,
        int(offset),
        int(page_limit),
    )
    payload["db_path"] = resolved
    payload["page_limit"] = int(page_limit)
    return JSONResponse(content=payload)


@app.get("/api/db/ping")
async def api_db_ping(db_path: Optional[str] = None) -> JSONResponse:
    """Return DB connectivity info without raising — used by the UI to test a path.

    Does **not** call ``ensure_chroma`` (that would repoint the global Chroma cache and disrupt
    active search/chat sessions). Uses a lightweight Chroma list_collections scan only.
    """
    resolved = resolve_db_path(form_path=db_path)
    db_dir = Path(resolved)
    exists = db_dir.is_dir()
    collection_names: List[str] = []
    embedding_model_detected: Optional[str] = None
    error: Optional[str] = None
    if query_mod is None:
        error = "query.py unavailable"
    else:

        def _scan() -> Tuple[List[str], Optional[str], Optional[str]]:
            try:
                client = _chroma_persistent_client_for_gui(resolved)
                cols = client.list_collections()
                names = [c.name for c in cols]
                model: Optional[str] = None
                if names:
                    m = query_mod.embedding_model_from_db_path(resolved)
                    model = (m or "").strip() or None
                return names, model, None
            except Exception as exc:
                return [], None, str(exc)

        names, model, err = await asyncio.to_thread(_scan)
        collection_names = names
        embedding_model_detected = model
        error = err

    return JSONResponse(
        content={
            "db_path": resolved,
            "exists": exists,
            "collection_names": collection_names,
            "embedding_model_detected": embedding_model_detected,
            "error": error,
        }
    )


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

    child_env = {**os.environ}
    emb = (body.embedding_model or "").strip() or "mxbai-embed-large"
    child_env["EMBEDDING_MODEL"] = emb
    if body.embed_workers is not None:
        child_env["EMBED_WORKERS"] = str(int(body.embed_workers))

    with _ingest_lock:
        if _ingest_busy:
            raise HTTPException(status_code=409, detail="An ingest job is already running")
        _ingest_busy = True

    async def event_stream() -> AsyncIterator[str]:
        global _ingest_proc, _ingest_busy
        proc: Optional[subprocess.Popen] = None

        # --- pre-flight info lines ------------------------------------------------
        db_disp = _argv_get_val(argv, "--db-path") or resolve_db_path()
        yield f"data: {json.dumps({'line': f'[GUI] DB path:     {db_disp}'})}\n\n"
        yield f"data: {json.dumps({'line': f'[GUI] Embed model: {emb}'})}\n\n"

        src_disp = _argv_get_source(argv)
        if src_disp:
            yield f"data: {json.dumps({'line': f'[GUI] Source:      {src_disp}'})}\n\n"

        # --- embedding model warmup probe -----------------------------------------
        try:
            import urllib.request as _ureq
            _req = _ureq.Request(
                "http://127.0.0.1:11434/api/embed",
                data=json.dumps({"model": emb, "input": "warmup"}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with _ureq.urlopen(_req, timeout=10):
                pass
        except Exception as _probe_exc:
            yield f"data: {json.dumps({'line': f'[GUI] WARNING: Ollama warmup for {emb} failed — run: ollama pull {emb}  ({_probe_exc})'})}\n\n"

        try:
            proc = subprocess.Popen(
                [sys.executable, *argv],
                cwd=str(REPO_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=child_env,
            )
            with _ingest_lock:
                _ingest_proc = proc

            assert proc.stdout is not None

            ingest_q: "queue.Queue[Optional[Tuple[str, Any]]]" = queue.Queue()
            # Short poll + rate-limited idle hints: ingest can go quiet during per-chunk LLM enrich
            # or huge single-file work; avoid spamming the same SSE line every few seconds.
            poll_sec = float(os.environ.get("RAG_GUI_INGEST_POLL_SEC", "12"))
            silence_before_idle = float(os.environ.get("RAG_GUI_INGEST_IDLE_AFTER_SILENCE_SEC", "42"))
            min_idle_repeat = float(os.environ.get("RAG_GUI_INGEST_IDLE_REPEAT_SEC", "90"))

            def _dequeue() -> Optional[Tuple[str, Any]]:
                try:
                    return ingest_q.get(timeout=poll_sec)
                except queue.Empty:
                    return ("idle", None)

            def _stdout_reader() -> None:
                assert proc.stdout is not None
                try:
                    for line in iter(proc.stdout.readline, ""):
                        if line:
                            ingest_q.put(
                                ("line", strip_ansi(line.rstrip("\n\r"))),
                            )
                    rest = proc.stdout.read()
                    if rest:
                        for raw in rest.splitlines():
                            ingest_q.put(("line", strip_ansi(raw)))
                    code = proc.wait()
                    ingest_q.put(("exit", int(code or 0)))
                except Exception as exc:
                    log.exception("ingest stdout reader")
                    ingest_q.put(("error", str(exc)))
                finally:
                    ingest_q.put(None)

            threading.Thread(target=_stdout_reader, daemon=True).start()

            stream_done_sent = False
            last_line_mono = time.monotonic()
            last_idle_msg_mono = 0.0
            while True:
                item = await asyncio.to_thread(_dequeue)
                if item is None:
                    break
                kind, payload = item
                if kind == "idle":
                    now = time.monotonic()
                    if now - last_line_mono < silence_before_idle:
                        continue
                    if now - last_idle_msg_mono < min_idle_repeat:
                        continue
                    last_idle_msg_mono = now
                    yield f"data: {json.dumps({'line': '[GUI] still running (no new log lines yet — large file, LLM enrich per chunk, or Chroma writer after embedding)…'})}\n\n"
                    continue
                if kind == "line":
                    last_line_mono = time.monotonic()
                    yield f"data: {json.dumps({'line': payload})}\n\n"
                    continue
                if kind == "exit":
                    yield f"data: {json.dumps({'done': True, 'exit_code': int(payload)})}\n\n"
                    stream_done_sent = True
                    break
                if kind == "error":
                    yield f"data: {json.dumps({'error': str(payload)})}\n\n"
                    yield f"data: {json.dumps({'done': True, 'exit_code': 1})}\n\n"
                    stream_done_sent = True
                    break
            if not stream_done_sent:
                yield f"data: {json.dumps({'error': 'Ingest log stream closed without subprocess exit code'})}\n\n"
                yield f"data: {json.dumps({'done': True, 'exit_code': 1})}\n\n"
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
    system_preset: str = "",
) -> str:
    raw = raw_query.strip()
    if len(history) < 2:
        return raw
    key = (api_key or "").strip()
    # Extended 10-message tail for better conversational context
    hist_tail = list(history[-10:])
    # RAG_REWRITE_MODEL is for Ollama only; never pass it to Anthropic/DeepSeek (wrong model IDs).
    ollama_rewrite_model = (RAG_REWRITE_MODEL or model or "").strip() or DEFAULT_DASHBOARD_LLM
    anthropic_rewrite_model = "claude-3-5-haiku-20241022"
    deepseek_rewrite_model = "deepseek-chat"

    # Add domain hint to rewrite prompt for ngspice preset
    domain_hint = ""
    if (system_preset or "").strip().lower() == "ngspice":
        domain_hint = " (domain: ngspice/SPICE circuit simulator C codebase)"

    rewrite_system = REWRITE_SYSTEM + domain_hint

    async def _attempt_ollama() -> str:
        msgs: List[Dict[str, str]] = (
            [{"role": "system", "content": rewrite_system}] + hist_tail + [{"role": "user", "content": raw}]
        )
        return await asyncio.to_thread(_rewrite_ollama_sync, msgs, ollama_rewrite_model)

    async def _attempt_cloud() -> str:
        if provider == "anthropic" and key:
            return await asyncio.to_thread(
                _rewrite_anthropic_sync, hist_tail, raw, anthropic_rewrite_model, key
            )
        if provider == "deepseek" and key:
            oa: List[Dict[str, str]] = (
                [{"role": "system", "content": rewrite_system}]
                + hist_tail
                + [{"role": "user", "content": raw}]
            )
            return await asyncio.to_thread(_rewrite_deepseek_sync, oa, deepseek_rewrite_model, key)
        return ""

    text = ""
    # Fallback chain: primary provider -> Ollama fallback -> raw
    try:
        if provider == "ollama" or not key:
            primary = _attempt_ollama()
        else:
            primary = _attempt_cloud()
        text = await asyncio.wait_for(primary, timeout=5.0)
    except (asyncio.TimeoutError, Exception) as exc:
        log.warning("Query rewrite primary failed (%s), falling back to Ollama", exc)
        if provider != "ollama":
            try:
                text = await asyncio.wait_for(_attempt_ollama(), timeout=5.0)
            except (asyncio.TimeoutError, Exception) as exc2:
                log.warning("Query rewrite Ollama fallback failed (%s), using raw query", exc2)
                return raw

    return _sanitize_rewritten_query(text, raw) if text else raw


@app.post("/api/query")
async def api_query(body: QueryBody) -> Any:
    if query_mod is None:
        raise HTTPException(status_code=503, detail="query.py unavailable")
    _reject_query_while_ingesting()
    # Only require Ollama when using the local model or when not in chat mode
    # (embedding retrieval uses Ollama but is guarded inside ensure_chroma)
    if body.llm_provider == "ollama" or not body.chat:
        if not await asyncio.to_thread(query_mod.check_ollama):
            raise HTTPException(
                status_code=503,
                detail="Ollama not reachable at http://127.0.0.1:11434 — start Ollama first",
            )

    db_path = resolve_db_path(form_path=body.db_path)
    _, _, cmap, _ = await ensure_chroma(db_path)
    if not cmap:
        raise HTTPException(
            status_code=400,
            detail=(
                "The vector database has no collections yet. Chroma opened this folder but "
                f"list_collections() is empty: {db_path!s}. "
                "Run ingestion with the same --db-path (or leave DB override empty so it matches "
                "RAG_GUI_DB_PATH / default Studio-Portable-RAG/VectorDB). "
                "If you already ingested elsewhere, point the GUI at that folder."
            ),
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
            system_preset=getattr(body, "system_preset", ""),
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
                    "conversation_id": body.conversation_id or "",
                    "llm_provider": body.llm_provider,
                    "llm_model": body.llm_model,
                    "chunk_count": len(hits),
                }
            )
            yield f"data: {json.dumps(done_payload)}\n\n"
        except Exception as exc:
            log.exception("SSE done payload failed")
            yield f"data: {json.dumps({'error': f'Serialize results failed: {exc!s}'})}\n\n"
            yield f"data: {json.dumps({'done': True, 'results': [], 'context_markdown': md_ctx, 'search_query': search_query, 'conversation_id': body.conversation_id or ''})}\n\n"

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
_AGENT_CTX_LIMIT = int(os.environ.get("RAG_AGENT_CTX_LIMIT", "120000"))

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

    tool_usage = """## Tool usage
Native function tools are attached to this request. Call at most one tool per turn, then wait for the tool result message before continuing.
"""
    if provider == "ollama":
        integrations = (
            "## Integrations\n"
            "- OpenAI-style tool JSON is available at GET /api/agent/tool-schemas.\n"
            "- This Ollama session uses native tool calling.\n"
        )
    else:
        integrations = (
            "## Integrations\n"
            "- OpenAI-style tool JSON (for custom clients) is available at GET /api/agent/tool-schemas.\n"
            "- This session uses native tool calling.\n"
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
    """Serialize conversation history for Ollama native tool calling.

    Converts internal _tool_calls_ollama / _tool_call_id markers to the
    Ollama chat API format so tool call history round-trips correctly.
    """
    out: List[Dict[str, Any]] = []
    for m in messages:
        role = m.get("role")
        if role == "assistant" and m.get("_tool_calls_ollama"):
            out.append({
                "role": "assistant",
                "content": m.get("content") or "",
                "tool_calls": m["_tool_calls_ollama"],
            })
        elif role == "user" and m.get("_tool_call_id"):
            out.append({
                "role": "tool",
                "content": _strip_tool_result_prefix(m.get("content", "")),
            })
        elif role in ("system", "user", "assistant"):
            out.append({"role": role, "content": m.get("content", "")})
    return out


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
        stream = om.chat(
            model=model,
            messages=clean,
            tools=_agent_tools_openai_style(),
            stream=True,
        )
    except Exception as exc:
        log.warning("agent ollama.chat failed: %s", exc)
        yield f"Error: Ollama call failed: {exc}"
        return

    text_parts: List[str] = []
    tool_name = ""
    tool_args: Dict[str, Any] = {}
    tool_found = False

    for chunk in stream:
        msg = chunk.get("message", {}) if isinstance(chunk, dict) else {}
        tok = msg.get("content", "")
        if tok:
            text_parts.append(tok)
            yield tok
        tcs = msg.get("tool_calls")
        if tcs:
            tool_found = True
            fn = tcs[0].get("function", {}) if isinstance(tcs[0], dict) else {}
            tool_name = fn.get("name", "") or ""
            raw_args = fn.get("arguments", {})
            if isinstance(raw_args, dict):
                tool_args = raw_args
            else:
                tool_args = _sanitize_json_args(str(raw_args))

    if tool_found and tool_name:
        yield _NativeToolCall(
            name=tool_name,
            kwargs=tool_args,
            tool_call_id="",
            text_before="".join(text_parts),
        )


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
    _in_think = False
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
            rc = getattr(delta, "reasoning_content", None)
            if rc:
                if not _in_think:
                    think_open = "<think>"
                    text_parts.append(think_open)
                    yield think_open
                    _in_think = True
                text_parts.append(rc)
                yield rc
            c = getattr(delta, "content", None)
            if c:
                if _in_think:
                    think_close = "</think>\n\n"
                    text_parts.append(think_close)
                    yield think_close
                    _in_think = False
                text_parts.append(c)
                yield c
            tcs = getattr(delta, "tool_calls", None)
            if not tcs:
                continue
            if _in_think:
                think_close = "</think>\n\n"
                text_parts.append(think_close)
                yield think_close
                _in_think = False
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
        if _in_think:
            think_close = "</think>\n\n"
            text_parts.append(think_close)
            yield think_close
            _in_think = False
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
        kwargs = _sanitize_json_args(raw_args)
        if not kwargs:
            log.warning("DeepSeek tool arguments JSON decode failed even after sanitization: %s", raw_args[:200])
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
        if orig_len > 2000:
            m["content"] = (
                m["content"][:2000] + f"\n... [Truncated tool result, was {orig_len} chars]"
            )


# ---------------------------------------------------------------------------
# Tool call parsing
# ---------------------------------------------------------------------------

_TOOL_CALL_RE = re.compile(r"<tool_call>(.*?)</tool_call>", re.DOTALL)
_TASK_DONE_RE = re.compile(r"<task_complete>(.*?)</task_complete>", re.DOTALL)
_MD_FENCE_RE = re.compile(r"```(?:json|JSON)?\s*\n?(.*?)\n?\s*```", re.DOTALL)
_TRAILING_COMMA_RE = re.compile(r",\s*([}\]])")


def _sanitize_json_args(raw: str) -> Dict[str, Any]:
    """Parse JSON tool arguments with a trailing-comma sanitization fallback."""
    try:
        result = json.loads(raw)
        return result if isinstance(result, dict) else {}
    except json.JSONDecodeError:
        sanitized = _TRAILING_COMMA_RE.sub(r"\1", raw)
        try:
            result = json.loads(sanitized)
            return result if isinstance(result, dict) else {}
        except json.JSONDecodeError:
            log.warning("tool args JSON unrecoverable after sanitization: %s", raw[:200])
            return {}


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
                elif ntm and prov == "ollama":
                    messages.append(
                        {
                            "role": "assistant",
                            "content": step_result["full_response"],
                            "_tool_calls_ollama": [
                                {
                                    "function": {
                                        "name": ntm["name"],
                                        "arguments": ntm["kwargs"],
                                    }
                                }
                            ],
                        }
                    )
                    messages.append(
                        {
                            "role": "user",
                            "content": f"[Tool Result: {step_result['tool_name']}]\n{tool_output}",
                            "_tool_call_id": ntm.get("tool_call_id") or "ollama-tc",
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
                    "All agent providers (Ollama, Anthropic, DeepSeek) use native tool calling "
                    "with these schemas. No XML <tool_call> tags are used."
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
