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
    ):
        self.session_id = session_id
        self.workspace_root = workspace_root.resolve()
        self.cmap = cmap
        self.db_path = db_path
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

    count = content.count(search_block)
    if count == 0:
        hint = _fuzzy_hint(content, search_block)
        return ToolResult(
            success=False, output="",
            error=f"Search block not found in {filepath}. {hint}Use read_file to see current content.",
        )
    if count > 1:
        return ToolResult(
            success=False, output="",
            error=f"Found {count} matches in {filepath}; include more surrounding context to make search_block unique.",
        )

    session.backup_file(target)
    new_content = content.replace(search_block, replace_block, 1)
    target.write_text(new_content, encoding="utf-8")
    idx = content.index(search_block)
    line_no = content[:idx].count("\n") + 1
    return ToolResult(
        success=True,
        output=f"Edited {filepath}: replaced {len(search_block)} chars at line {line_no}",
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
) -> ToolResult:
    if query_mod is None:
        return ToolResult(success=False, output="", error="query.py module not available")
    if not session.cmap:
        return ToolResult(success=False, output="", error="No vector DB collections loaded")
    try:
        hits = query_mod._sync_multi_search(
            query, top_k, "auto", domain, "", session.cmap, session.db_path,
        )
        if not hits:
            return ToolResult(success=True, output="No matching results found.")
        md = query_mod.format_markdown(hits, query)
        return ToolResult(success=True, output=md)
    except Exception as exc:
        return ToolResult(success=False, output="", error=f"Search error: {exc}")


# ---------------------------------------------------------------------------
# TOOL_REGISTRY and TOOL_DESCRIPTIONS
# ---------------------------------------------------------------------------

TOOL_REGISTRY: Dict[str, Callable[..., ToolResult]] = {
    "read_file": read_file,
    "edit_file": edit_file,
    "create_file": create_file,
    "run_terminal_command": run_terminal_command,
    "search_codebase": search_codebase,
}

_TOOL_DESC_LINES = [
    "read_file(filepath, start_line?, end_line?) — Read a file or line range. Lines are 1-indexed.",
    "edit_file(filepath, search_block, replace_block) — Replace an exact substring in a file. Include 3+ surrounding lines for uniqueness. Always read_file first.",
    "create_file(filepath, content) — Create a new file. Fails if it already exists.",
    "run_terminal_command(command, cwd?, timeout?) — Run a shell command. Default timeout 30s. cwd is relative to workspace. Blocklist + timeout only; not a sandbox.",
    "search_codebase(query, domain?, top_k?) — Search the ingested RAG vector database.",
]

# Backward-compatible combined string (includes shell line; use tool_descriptions_for_agent_prompt for LLM)
TOOL_DESCRIPTIONS = "\n".join(_TOOL_DESC_LINES)


def tool_descriptions_for_agent_prompt() -> str:
    """Tool list for the agent system prompt (omits shell when RAG_AGENT_ALLOW_SHELL disables it)."""
    if is_agent_shell_enabled():
        return "\n".join(_TOOL_DESC_LINES)
    return "\n".join(
        line for line in _TOOL_DESC_LINES if not line.startswith("run_terminal_command")
    )
