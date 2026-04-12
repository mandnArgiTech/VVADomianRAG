"""
agent_tools.py — Tool registry and session management for the autonomous coding agent.

Provides sandboxed file I/O, terminal execution, and RAG search tools,
plus backup/rollback via AgentSession.
"""
from __future__ import annotations

import difflib
import logging
import os
import re
import shutil
import subprocess
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

log = logging.getLogger("agent_tools")

# ---------------------------------------------------------------------------
# ToolResult — universal return type for every tool
# ---------------------------------------------------------------------------

@dataclass
class ToolResult:
    success: bool
    output: str
    error: str = ""


# ---------------------------------------------------------------------------
# AgentSession — per-session state, backup/rollback, path security
# ---------------------------------------------------------------------------

class AgentSession:
    """Tracks file mutations and provides rollback for one agent run."""

    def __init__(
        self,
        session_id: str,
        workspace_root: Path,
        cmap: Dict[str, Any],
        db_path: str,
        chroma_client: Optional[Any] = None,
        chroma_embedder: Optional[Any] = None,
    ):
        self.session_id = session_id
        self.workspace_root = workspace_root.resolve()
        self.cmap = cmap
        self.db_path = db_path
        self.chroma_client = chroma_client
        self.chroma_embedder = chroma_embedder
        self.backed_up: Dict[str, Path] = {}  # rel_path -> backup_path
        self.created_files: Set[str] = set()   # rel_paths created by the agent
        self._backup_dir = self.workspace_root / ".rag_agent_backups" / session_id

    # -- path security -------------------------------------------------------

    def resolve_path(self, rel: str) -> Path:
        """Resolve *rel* under workspace root; raise on traversal escape."""
        piece = rel.strip().replace("\\", "/").lstrip("/")
        if ".." in Path(piece).parts:
            raise ValueError("Path cannot use ..")
        target = (self.workspace_root / piece).resolve()
        try:
            target.relative_to(self.workspace_root)
        except ValueError:
            raise ValueError(
                f"Path escapes workspace: {rel!r} resolves to {target}"
            )
        return target

    # -- backup / rollback ---------------------------------------------------

    def backup_file(self, abs_path: Path) -> None:
        """Copy *abs_path* into the session backup dir (first touch only)."""
        rel = str(abs_path.resolve().relative_to(self.workspace_root))
        if rel in self.backed_up:
            return
        dest = self._backup_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(abs_path), str(dest))
        self.backed_up[rel] = dest

    def rollback(self) -> List[str]:
        """Restore backed-up files and delete agent-created files."""
        restored: List[str] = []
        for rel, bkp in self.backed_up.items():
            target = self.workspace_root / rel
            try:
                shutil.copy2(str(bkp), str(target))
                restored.append(f"restored {rel}")
            except Exception as exc:
                log.warning("rollback failed for %s: %s", rel, exc)
                restored.append(f"FAILED to restore {rel}: {exc}")
        for rel in self.created_files:
            target = self.workspace_root / rel
            try:
                if target.is_file():
                    target.unlink()
                    restored.append(f"deleted created file {rel}")
            except Exception as exc:
                log.warning("rollback delete failed for %s: %s", rel, exc)
                restored.append(f"FAILED to delete {rel}: {exc}")
        self._remove_backup_dir()
        return restored

    def cleanup(self) -> None:
        """Remove backup dir after a successful task_complete."""
        self._remove_backup_dir()

    def _remove_backup_dir(self) -> None:
        try:
            if self._backup_dir.is_dir():
                shutil.rmtree(str(self._backup_dir))
        except Exception as exc:
            log.warning("cleanup backup dir failed: %s", exc)


# ---------------------------------------------------------------------------
# Tool functions (all synchronous — called via asyncio.to_thread)
# ---------------------------------------------------------------------------

_FILE_READ_CAP = 10_000  # chars
_STDOUT_CAP = 8_000
_STDERR_CAP = 4_000

# -- read_file ---------------------------------------------------------------

def read_file(
    session: AgentSession,
    filepath: str,
    start_line: Optional[int] = None,
    end_line: Optional[int] = None,
) -> ToolResult:
    try:
        target = session.resolve_path(filepath)
    except ValueError as exc:
        return ToolResult(success=False, output="", error=str(exc))
    if not target.is_file():
        return ToolResult(success=False, output="", error=f"File not found: {filepath}")
    try:
        text = target.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return ToolResult(success=False, output="", error=f"Read error: {exc}")
    lines = text.splitlines(keepends=True)
    total = len(lines)
    if start_line is not None or end_line is not None:
        s = max(1, start_line or 1) - 1
        e = min(total, end_line or total)
        lines = lines[s:e]
        offset = s
    else:
        offset = 0
    width = len(str(offset + len(lines)))
    numbered = []
    for i, ln in enumerate(lines, start=offset + 1):
        numbered.append(f"{i:>{width}} | {ln.rstrip()}")
    content = "\n".join(numbered)
    if len(content) > _FILE_READ_CAP:
        content = content[:_FILE_READ_CAP] + f"\n... [truncated, {total} lines total]"
    return ToolResult(success=True, output=content)


# -- edit_file ---------------------------------------------------------------

def _normalize_for_edit(text: str) -> str:
    """Normalize line endings and strip trailing whitespace per line for fuzzy matching."""
    return "\n".join(
        line.rstrip()
        for line in text.replace("\r\n", "\n").replace("\r", "\n").splitlines()
    )


def edit_file(
    session: AgentSession,
    filepath: str,
    search_block: str,
    replace_block: str,
) -> ToolResult:
    try:
        target = session.resolve_path(filepath)
    except ValueError as exc:
        return ToolResult(success=False, output="", error=str(exc))
    if not target.is_file():
        return ToolResult(success=False, output="", error=f"File not found: {filepath}. Use create_file for new files.")
    try:
        content = target.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return ToolResult(success=False, output="", error=f"Read error: {exc}")

    # Tier 1: exact match on original content
    count = content.count(search_block)
    if count > 1:
        return ToolResult(
            success=False, output="",
            error=f"Found {count} matches in {filepath}; include more surrounding context to make search_block unique.",
        )
    if count == 1:
        session.backup_file(target)
        new_content = content.replace(search_block, replace_block, 1)
        target.write_text(new_content, encoding="utf-8")
        idx = content.index(search_block)
        line_no = content[:idx].count("\n") + 1
        return ToolResult(
            success=True,
            output=f"Edited {filepath}: replaced {len(search_block)} chars at line {line_no}",
        )

    # Tier 2: normalized whitespace exact match
    norm_content = _normalize_for_edit(content)
    norm_search = _normalize_for_edit(search_block)
    norm_count = norm_content.count(norm_search)
    if norm_count > 1:
        return ToolResult(
            success=False, output="",
            error=f"Ambiguous: {norm_count} normalized matches in {filepath}. Add more surrounding context to make search_block unique.",
        )
    if norm_count == 1:
        session.backup_file(target)
        new_content = norm_content.replace(norm_search, replace_block, 1)
        target.write_text(new_content, encoding="utf-8")
        return ToolResult(
            success=True,
            output=f"Edited {filepath} (normalized whitespace match — trailing spaces were stripped)",
        )

    # Tier 3: fuzzy auto-correct (ratio > 0.90)
    file_lines = norm_content.splitlines()
    search_lines = norm_search.splitlines()
    n = len(search_lines)
    best_ratio = 0.0
    best_start = -1
    if n > 0 and n <= len(file_lines):
        for i in range(len(file_lines) - n + 1):
            window = "\n".join(file_lines[i : i + n])
            r = difflib.SequenceMatcher(None, norm_search, window).ratio()
            if r > best_ratio:
                best_ratio, best_start = r, i
    if best_ratio > 0.90 and best_start >= 0:
        best_block = "\n".join(file_lines[best_start : best_start + n])
        session.backup_file(target)
        new_content = norm_content.replace(best_block, replace_block, 1)
        target.write_text(new_content, encoding="utf-8")
        log.warning("edit_file auto-corrected %.0f%% match in %s", best_ratio * 100, filepath)
        return ToolResult(
            success=True,
            output=(
                f"Edited {filepath} (auto-corrected {best_ratio:.0%} fuzzy match — "
                f"search_block whitespace was normalized to match file content)"
            ),
        )

    hint = _fuzzy_hint(content, search_block)
    return ToolResult(
        success=False, output="",
        error=f"Search block not found in {filepath}. {hint}Use read_file to see current content.",
    )


def _fuzzy_hint(content: str, search_block: str) -> str:
    """Find the closest matching region and return a hint string."""
    file_lines = content.splitlines()
    search_lines = search_block.splitlines()
    if not search_lines or not file_lines:
        return ""
    best_ratio = 0.0
    best_line = 0
    best_preview = ""
    n = len(search_lines)
    if n > len(file_lines):
        chunk = "\n".join(file_lines)
        ratio = difflib.SequenceMatcher(None, search_block, chunk).ratio()
        if ratio > 0.4:
            return f"Closest match ({ratio:.0%}) in file (block longer than file): '{chunk[:120]}...'. "
        return ""
    for i in range(0, len(file_lines) - n + 1):
        chunk = "\n".join(file_lines[i : i + n])
        ratio = difflib.SequenceMatcher(None, search_block, chunk).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_line = i + 1
            best_preview = chunk[:120]
    if best_ratio > 0.4:
        return f"Closest match ({best_ratio:.0%}) at line {best_line}: '{best_preview}...'. "
    return ""


# -- create_file -------------------------------------------------------------

def create_file(
    session: AgentSession,
    filepath: str,
    content: str,
) -> ToolResult:
    try:
        target = session.resolve_path(filepath)
    except ValueError as exc:
        return ToolResult(success=False, output="", error=str(exc))
    if target.exists():
        return ToolResult(
            success=False, output="",
            error=f"File already exists: {filepath}. Use edit_file to modify existing files.",
        )
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    except Exception as exc:
        return ToolResult(success=False, output="", error=f"Create error: {exc}")
    rel = str(target.resolve().relative_to(session.workspace_root))
    session.created_files.add(rel)
    n = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
    return ToolResult(success=True, output=f"Created {filepath} ({n} lines)")


# -- run_terminal_command ----------------------------------------------------

def is_agent_shell_enabled() -> bool:
    """If false, run_terminal_command is rejected (RAG_AGENT_ALLOW_SHELL=0/false/no/off)."""
    v = os.environ.get("RAG_AGENT_ALLOW_SHELL", "true").strip().lower()
    return v not in ("0", "false", "no", "off")


# Heuristic blocklist only — not a security boundary; bypassable by obfuscation.
_BLOCKED_PATTERNS = [
    re.compile(r"\brm\s+.*-[rf]{2,}.*\s+(/|~/|/home|/etc|/usr|/var|/boot)\b"),
    re.compile(r"\brm\s+.*-[rf]{2,}\s+/\s*$"),
    re.compile(r"\brm\s+.*-[rf]{2,}\s+/\s+\S"),
    re.compile(r"\bsudo\s+rm\b"),
    re.compile(r"\bmkfs\b"),
    re.compile(r"\bdd\s+if="),
    re.compile(r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;"),  # fork bomb
    re.compile(r">\s*/dev/sd[a-z]"),
    re.compile(r"\bchmod\s+-R\s+777\s+/\s*$"),
    re.compile(r"\b(shutdown|reboot|init\s+0|halt|poweroff)\b"),
    re.compile(r"\bkill\s+-9\s+1\b"),
    re.compile(r"\bcurl\s+[^\n|]+\|\s*(ba)?sh\b"),
    re.compile(r"\bwget\s+[^\n|]+\|\s*(ba)?sh\b"),
    re.compile(r"\bcurl\s+[^\n|]+\|\s*sudo\b"),
    re.compile(r"\bpython\s+[^\n|]+\|\s*(ba)?sh\b"),
]


def _cmd_timeout_default() -> int:
    try:
        return max(1, int(os.environ.get("RAG_AGENT_CMD_TIMEOUT", "30")))
    except ValueError:
        return 30


def run_terminal_command(
    session: AgentSession,
    command: str,
    cwd: Optional[str] = None,
    timeout: Optional[int] = None,
) -> ToolResult:
    if not is_agent_shell_enabled():
        return ToolResult(
            success=False,
            output="",
            error="run_terminal_command is disabled on this server (RAG_AGENT_ALLOW_SHELL=0).",
        )
    if timeout is None:
        timeout = _cmd_timeout_default()
    cmd_lower = command.strip().lower()
    for pat in _BLOCKED_PATTERNS:
        if pat.search(cmd_lower):
            return ToolResult(
                success=False, output="",
                error=f"Blocked: command matches a dangerous pattern. Command: {command}",
            )

    if cwd:
        try:
            resolved_cwd = str(session.resolve_path(cwd))
        except ValueError as exc:
            return ToolResult(success=False, output="", error=str(exc))
    else:
        resolved_cwd = str(session.workspace_root)

    try:
        proc = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=resolved_cwd,
        )
        stdout = proc.stdout[:_STDOUT_CAP] if proc.stdout else ""
        stderr = proc.stderr[:_STDERR_CAP] if proc.stderr else ""
        out = f"exit_code={proc.returncode}\n--- stdout ---\n{stdout}\n--- stderr ---\n{stderr}"
        return ToolResult(success=(proc.returncode == 0), output=out)
    except subprocess.TimeoutExpired:
        return ToolResult(
            success=False, output="",
            error=f"Command timed out after {timeout}s: {command}",
        )
    except Exception as exc:
        return ToolResult(success=False, output="", error=f"Execution error: {exc}")


# -- search_codebase ---------------------------------------------------------

def search_codebase(
    session: AgentSession,
    query: str,
    query_mod: Any,
    domain: str = "",
    top_k: int = 5,
    search_type: str = "auto",
) -> ToolResult:
    if query_mod is None:
        return ToolResult(success=False, output="", error="query.py module not available")
    if not session.cmap:
        return ToolResult(success=False, output="", error="No vector DB collections loaded")
    st = (search_type or "auto").strip().lower()
    if st not in ("auto", "code", "domain", "troubleshoot", "reference"):
        st = "auto"
    try:
        hits = query_mod._sync_multi_search_with_dependency_hop(
            query, top_k, st, domain, "", session.cmap, session.db_path,
        )
        if not hits:
            return ToolResult(success=True, output="No matching results found.")
        primary = [h for h in hits if getattr(h, "retrieval_hop", None) != "dependency"]
        deps = [h for h in hits if getattr(h, "retrieval_hop", None) == "dependency"]
        md = query_mod.format_markdown(primary, query)
        if deps:
            md += "\n\n## Dependent Headers / Context\n\n"
            md += (
                "*Chunks whose `dependencies` metadata reference symbols from the primary hits "
                "(e.g. headers / structs used by the C files above).*\n\n"
            )
            md += query_mod.format_markdown(deps, query)
        return ToolResult(success=True, output=md)
    except Exception as exc:
        return ToolResult(success=False, output="", error=f"Search error: {exc}")


# ---------------------------------------------------------------------------
# Web search tool
# ---------------------------------------------------------------------------

_DDGS_AVAILABLE: Optional[bool] = None
_DDGS_IMPL: str = ""  # "ddgs" | "duckduckgo_search"


def _check_ddgs() -> bool:
    global _DDGS_AVAILABLE, _DDGS_IMPL
    if _DDGS_AVAILABLE is None:
        try:
            from ddgs import DDGS  # noqa: F401

            _DDGS_AVAILABLE = True
            _DDGS_IMPL = "ddgs"
        except ImportError:
            try:
                from duckduckgo_search import DDGS  # noqa: F401

                _DDGS_AVAILABLE = True
                _DDGS_IMPL = "duckduckgo_search"
            except ImportError:
                _DDGS_AVAILABLE = False
                _DDGS_IMPL = ""
    return _DDGS_AVAILABLE


def web_search(
    session: Optional[AgentSession] = None,
    query: str = "",
    max_results: int = 3,
) -> ToolResult:
    """Search the web via ddgs (preferred) or duckduckgo-search; return top results as markdown."""
    if not _check_ddgs():
        return ToolResult(
            success=False, output="",
            error="Install web search: pip install ddgs   (or: pip install duckduckgo-search)",
        )
    k = min(max_results, 5)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            if _DDGS_IMPL == "ddgs":
                from ddgs import DDGS

                with DDGS() as ddgs:
                    results = list(ddgs.text(query, max_results=k))
            else:
                from duckduckgo_search import DDGS

                with DDGS() as ddgs:
                    results = list(ddgs.text(query, max_results=k))
        if not results:
            return ToolResult(success=True, output="No web results found for that query.")
        parts: List[str] = []
        for i, r in enumerate(results, 1):
            title = r.get("title", "Untitled")
            body = r.get("body", "")
            href = r.get("href", "")
            parts.append(f"### {i}. {title}\n{body}\n[Source]({href})")
        return ToolResult(success=True, output="\n\n".join(parts))
    except Exception as exc:
        return ToolResult(success=False, output="", error=f"Web search failed: {exc}")


# ---------------------------------------------------------------------------
# Long-term memory tool — write + ingest into VectorDB
# ---------------------------------------------------------------------------

_TOOLS_REPO_ROOT = Path(__file__).resolve().parent
_SP_RAG = _TOOLS_REPO_ROOT / "Studio-Portable-RAG"
_MEMORY_SUBDIRS = {
    "domain_docs": _SP_RAG / "DomainDocs",
    "wiki": _SP_RAG / "Wiki",
}

_TITLE_SANITIZE_RE = re.compile(r"[^\w\s\-]")


def _memory_root_for_storage(storage: str) -> Path:
    st = (storage or "domain_docs").strip().lower().replace("-", "_")
    if st == "wiki":
        return _MEMORY_SUBDIRS["wiki"]
    return _MEMORY_SUBDIRS["domain_docs"]


def remember_concept(
    session: AgentSession,
    title: str,
    content: str,
    domain: str = "general",
    storage: str = "domain_docs",
) -> ToolResult:
    """Save knowledge under Studio-Portable-RAG/DomainDocs or .../Wiki and ingest into VectorDB."""
    safe_title = _TITLE_SANITIZE_RE.sub("", title).strip().replace(" ", "_")[:80]
    if not safe_title:
        return ToolResult(success=False, output="", error="Title is empty after sanitization.")
    root = _memory_root_for_storage(storage)
    root.mkdir(parents=True, exist_ok=True)
    filepath = (root / f"{safe_title}.md").resolve()
    try:
        filepath.relative_to(root.resolve())
    except ValueError:
        return ToolResult(success=False, output="", error="Invalid title: path traversal detected.")

    try:
        filepath.write_text(content, encoding="utf-8")
    except Exception as exc:
        return ToolResult(success=False, output="", error=f"Failed to write file: {exc}")

    try:
        from domain_feeder import feed_domain_document

        try:
            import query as _query_mod

            embed_model = _query_mod.embedding_model_from_db_path(session.db_path)
        except Exception:
            embed_model = "nomic-embed-text"
        stats = feed_domain_document(
            filepath=str(filepath),
            domain=domain or "general",
            db_path=session.db_path,
            embed_model=embed_model,
            source_type="domain_doc",
            chroma_client=session.chroma_client,
            embedder=session.chroma_embedder,
        )
        chunk_count = stats.get("chunk_count", stats.get("chunks_upserted", "?"))
        try:
            rel_disp = str(filepath.relative_to(_TOOLS_REPO_ROOT))
        except ValueError:
            rel_disp = str(filepath)
        return ToolResult(
            success=True,
            output=f"Saved '{title}' to {rel_disp} and ingested into VectorDB ({chunk_count} chunks).",
        )
    except ImportError:
        try:
            rel_disp = str(filepath.relative_to(_TOOLS_REPO_ROOT))
        except ValueError:
            rel_disp = str(filepath)
        return ToolResult(
            success=False,
            output="",
            error=(
                f"File saved to {rel_disp} but domain_feeder is unavailable — "
                "run ingestion on that path manually."
            ),
        )
    except Exception as exc:
        try:
            rel_disp = str(filepath.relative_to(_TOOLS_REPO_ROOT))
        except ValueError:
            rel_disp = str(filepath)
        return ToolResult(
            success=False,
            output="",
            error=(
                f"File saved to {rel_disp} but RAG ingestion failed: {exc}. "
                "Re-run ingest on DomainDocs/Wiki or fix Ollama/embeddings, then retry remember_concept."
            ),
        )


# ---------------------------------------------------------------------------
# TOOL_REGISTRY and TOOL_DESCRIPTIONS
# ---------------------------------------------------------------------------

TOOL_REGISTRY: Dict[str, Callable[..., ToolResult]] = {
    "read_file": read_file,
    "edit_file": edit_file,
    "create_file": create_file,
    "run_terminal_command": run_terminal_command,
    "search_codebase": search_codebase,
    "web_search": web_search,
    "remember_concept": remember_concept,
}

_TOOL_DESC_LINES = [
    "read_file(filepath, start_line?, end_line?) — Read a file or line range. Lines are 1-indexed.",
    "edit_file(filepath, search_block, replace_block) — Replace an exact substring in a file. Include 3+ surrounding lines for uniqueness. Always read_file first.",
    "create_file(filepath, content) — Create a new file. Fails if it already exists.",
    "run_terminal_command(command, cwd?, timeout?) — Run a shell command. Default timeout 30s. cwd is relative to workspace. Blocklist + timeout only; not a sandbox.",
    "search_codebase(query, domain?, top_k?, search_type?) — Search RAG. search_type: auto|code|domain|troubleshoot|reference.",
    "web_search(query, max_results?) — Search the web via DuckDuckGo. Returns top results as markdown.",
    "remember_concept(title, content, domain?, storage?) — Save to DomainDocs/ (default) or Wiki/ (storage=wiki); ingest into VectorDB.",
]

_SHELL_LINE_PREFIX = "run_terminal_command"

TOOL_DESCRIPTIONS = "\n".join(_TOOL_DESC_LINES)


def tool_descriptions_for_agent_prompt() -> str:
    """Tool list for the agent system prompt (omits shell when RAG_AGENT_ALLOW_SHELL disables it)."""
    if is_agent_shell_enabled():
        return "\n".join(_TOOL_DESC_LINES)
    return "\n".join(
        line for line in _TOOL_DESC_LINES if not line.startswith(_SHELL_LINE_PREFIX)
    )
