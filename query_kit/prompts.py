"""Load domain markdown prompts and resolve effective system prompt from retrieval hits."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from util.search_primitives import SearchHit

from query_kit.config import QUERY_PROMPT_DOC_THRESHOLD, QUERY_PROMPT_TOP_M
from query_kit.prompt_strings import (
    DEBUG_SYSTEM_PROMPT,
    DEFAULT_SYSTEM_PROMPT,
    GENERIC_SYSTEM_PROMPT,
)

# Repository root: query_kit/prompts.py -> parent.parent == VVADomianRAG when laid out as query_kit/
_REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROMPTS_DIR = _REPO_ROOT / "system_prompts"


def load_system_prompt(
    domain: str,
    prompts_dir: Optional[Path] = None,
    *,
    _prompts_dir: Optional[Path] = None,
) -> str:
    """Load ``system_prompts/{domain}_engineer.md``; if missing, ``default.md``.

    When ``domain`` is empty, returns ``""``.

    ``prompts_dir`` (or legacy ``_prompts_dir``) overrides the default ``<repo>/system_prompts``.
    """
    sdir = prompts_dir if prompts_dir is not None else (_prompts_dir if _prompts_dir is not None else DEFAULT_PROMPTS_DIR)
    d = (domain or "").strip().lower()
    if not d:
        return ""
    p = sdir / f"{d}_engineer.md"
    if p.is_file():
        try:
            return p.read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            return ""
    p0 = sdir / "default.md"
    if p0.is_file():
        try:
            return p0.read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            return ""
    return ""


def effective_system_prompt(
    hits: List[SearchHit],
    search_type: str,
    override: Optional[str],
    domain: str = "",
    *,
    prompts_dir: Optional[Path] = None,
    _prompts_dir: Optional[Path] = None,
) -> str:
    """Pick generic vs debug persona from top-hit source types unless user overrode.

    When ``domain`` is set and a markdown prompt exists under ``prompts_dir`` (or legacy
    ``_prompts_dir``), that text is prepended (see ``load_system_prompt``).
    """
    if override is not None:
        return override
    if not hits:
        base = DEFAULT_SYSTEM_PROMPT
    else:
        m = min(QUERY_PROMPT_TOP_M, len(hits))
        docish = {"rally", "customer", "community"}
        cnt = sum(1 for h in hits[:m] if h.source_type in docish)
        if m > 0 and cnt / m >= QUERY_PROMPT_DOC_THRESHOLD:
            if search_type.lower() == "troubleshoot":
                base = DEBUG_SYSTEM_PROMPT
            else:
                base = GENERIC_SYSTEM_PROMPT
        else:
            base = GENERIC_SYSTEM_PROMPT
    pd = prompts_dir if prompts_dir is not None else _prompts_dir
    dp = (load_system_prompt(domain, prompts_dir=pd) or "").strip()
    if dp:
        return f"{dp}\n\n---\n\n{base}"
    return base


# Historical names (tests / shim)
_load_system_prompt = load_system_prompt
_effective_system_prompt = effective_system_prompt
