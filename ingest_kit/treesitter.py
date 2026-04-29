"""Optional tree-sitter language loading (lazy grammar modules)."""

from __future__ import annotations

from typing import Any, Dict


_TS_LANG: Dict[str, Any] = {}


class TreeSitterFallbackDisallowedError(RuntimeError):
    """Tree-sitter is unavailable and RecursiveCharacterTextSplitter fallback was not opted in."""


def _load_ts_language(name: str, mod_name: str) -> Any:
    if name in _TS_LANG:
        return _TS_LANG[name]
    try:
        mod = __import__(mod_name, fromlist=["language"])
        from tree_sitter import Language as TSLanguage  # type: ignore

        lang = TSLanguage(getattr(mod, "language")())
        _TS_LANG[name] = lang
        return lang
    except Exception:  # pragma: no cover
        return None


def _ts_parser_for(lang_name: str, mod_name: str):
    from tree_sitter import Parser  # type: ignore

    lang = _load_ts_language(lang_name, mod_name)
    if lang is None:
        return None  # pragma: no cover
    try:
        return Parser(lang)  # tree-sitter-python >=0.21
    except TypeError:  # pragma: no cover
        p = Parser()
        if hasattr(p, "set_language"):
            p.set_language(lang)
        else:
            p.language = lang  # type: ignore[attr-defined]
        return p
