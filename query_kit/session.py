"""Mutable REPL configuration derived from argparse."""

from __future__ import annotations

import argparse
from typing import Optional

from util.constants import MAX_K

from query_kit.ollama_client import default_chat_llm_from_env


class SessionState:
    def __init__(self, ns: argparse.Namespace) -> None:
        self.domain = ns.domain or ""
        self.repo = ns.repo or ""
        self.top_k = max(1, min(int(ns.top_k), MAX_K))
        self.search_type = ns.search_type
        self.out_format = ns.format
        self.mode = ns.mode  # semantic | concept | codebase
        self.timeout = int(ns.timeout)
        self.chat = bool(getattr(ns, "chat", False))
        cli_llm = (getattr(ns, "llm_model", None) or "").strip()
        self.llm_model = cli_llm or default_chat_llm_from_env()
        sp = (getattr(ns, "system_prompt", None) or "").strip()
        self.system_prompt_override: Optional[str] = sp if sp else None
        self.history_depth = max(1, int(getattr(ns, "history_depth", 5)))

    def apply_set(self, key: str, value: str) -> str:
        k = key.lower().strip()
        v = value.strip()
        if k == "domain":
            self.domain = v
        elif k == "k" or k == "top_k":
            try:
                self.top_k = max(1, min(int(v), MAX_K))
            except ValueError:
                return "k must be an integer"
        elif k == "type" or k == "search-type":
            allowed = {"auto", "code", "domain", "troubleshoot", "reference"}
            if v not in allowed:
                return f"type must be one of: {', '.join(sorted(allowed))}"
            self.search_type = v
        elif k == "repo":
            self.repo = v
        elif k == "format":
            if v not in ("markdown", "json", "plain"):
                return "format must be markdown, json, or plain"
            self.out_format = v
        elif k == "mode":
            if v not in ("semantic", "concept", "codebase"):
                return "mode must be semantic, concept, or codebase (use /status for DB status)"
            self.mode = v
        elif k == "timeout":
            try:
                self.timeout = max(1, int(v))
            except ValueError:
                return "timeout must be an integer"
        elif k in ("history_depth", "history-depth"):
            try:
                self.history_depth = max(1, int(v))
            except ValueError:
                return "history_depth must be an integer"
        elif k == "chat":
            if v.lower() in ("1", "true", "yes", "on"):
                self.chat = True
            elif v.lower() in ("0", "false", "no", "off"):
                self.chat = False
            else:
                return "chat must be on or off"
        else:
            return f"Unknown key: {key}"
        return f"OK: {k} = {v!r}"

    def show(self) -> str:
        return (
            f"domain={self.domain!r} repo={self.repo!r} k={self.top_k} "
            f"search_type={self.search_type!r} format={self.out_format!r} "
            f"mode={self.mode!r} timeout={self.timeout} chat={self.chat} "
            f"llm_model={self.llm_model!r} history_depth={self.history_depth}"
        )
