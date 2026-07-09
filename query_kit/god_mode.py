"""God-mode chunk_name prefetch and BM25 typo expansion (symbols_vocabulary.json)."""

from __future__ import annotations

import difflib
import json
import os
import re
import threading
from pathlib import Path
from typing import Dict, List

_vocab_cache: Dict[str, frozenset] = {}
_vocab_lock = threading.Lock()
# Lowercase->canonical maps, keyed by the vocab frozenset itself (frozensets
# cache their hash, so lookups are cheap). Rebuilding this dict per query is
# O(vocab) and shows up on every search with a large symbols_vocabulary.json.
_lower_map_cache: Dict[frozenset, Dict[str, str]] = {}


def _canon_lower_map(vocab: frozenset) -> Dict[str, str]:
    m = _lower_map_cache.get(vocab)
    if m is None:
        with _vocab_lock:
            m = _lower_map_cache.get(vocab)
            if m is None:
                m = {v.lower(): v for v in vocab}
                _lower_map_cache[vocab] = m
    return m

_GOD_MODE_STEM_DENYLIST: frozenset = frozenset(
    {
        "terminal",
        "main",
        "init",
        "util",
        "utils",
        "helper",
        "helpers",
        "common",
        "config",
        "test",
        "tests",
        "setup",
        "build",
        "makefile",
        "readme",
        "changelog",
        "license",
        "todo",
        "fixme",
    }
)


def is_noise_stem(name: str, query_raw: str) -> bool:
    """True if *name* is denylisted and the query does not name the file (e.g. ``terminal.c``)."""
    n = (name or "").strip().lower()
    if n not in _GOD_MODE_STEM_DENYLIST:
        return False
    return not re.search(rf"\b{re.escape(n)}\.[a-zA-Z]+\b", query_raw or "", re.IGNORECASE)


def load_symbols_vocab(db_path: str) -> frozenset:
    root = (db_path or "").strip()
    if not root:
        return frozenset()
    key = os.path.abspath(root)
    cached = _vocab_cache.get(key)
    if cached is not None:
        return cached
    with _vocab_lock:
        cached = _vocab_cache.get(key)
        if cached is not None:
            return cached
        p = Path(key) / "symbols_vocabulary.json"
        if not p.is_file():
            _vocab_cache[key] = frozenset()
            return _vocab_cache[key]
        try:
            raw = json.loads(p.read_text(encoding="utf-8", errors="replace"))
            if isinstance(raw, list):
                vocab = frozenset(str(x) for x in raw if str(x).strip())
            elif isinstance(raw, dict) and "symbols" in raw:
                vocab = frozenset(str(x) for x in raw["symbols"] if str(x).strip())
            else:
                vocab = frozenset()
        except Exception:
            vocab = frozenset()
        _vocab_cache[key] = vocab
        return vocab


def god_mode_chunk_name_matches(query_raw: str, vocab: frozenset) -> List[str]:
    """Build ``chunk_name`` values for Chroma ``$in`` God-mode (exact + case-insensitive vocab)."""
    q = (query_raw or "").strip()
    if not q or not vocab:
        return []
    tokens = set(re.findall(r"[\w\.]+", q))
    canon_lower: Dict[str, str] = _canon_lower_map(vocab)
    out: List[str] = []
    seen: set = set()

    def add(name: str) -> None:
        n = (name or "").strip()
        if n and n not in seen:
            out.append(n)
            seen.add(n)

    for t in tokens:
        if t in vocab:
            if not is_noise_stem(t, q):
                add(t)
            continue
        c = canon_lower.get(t.lower())
        if c and not is_noise_stem(c, q):
            add(c)

    if " " not in q:
        cq = canon_lower.get(q.lower())
        if q not in seen and (cq is None or cq not in seen):
            if q in vocab:
                if not is_noise_stem(q, q):
                    add(q)
            elif cq:
                if not is_noise_stem(cq, q):
                    add(cq)
            else:
                add(q)
    return out


def expand_query_typos(query: str, vocab: frozenset) -> str:
    if not vocab or not (query or "").strip():
        return query
    tokens = re.findall(r"[\w\.]+", query)
    vocab_lower_map = _canon_lower_map(vocab)
    expansions: List[str] = []
    for tok in tokens:
        if tok.lower() in vocab_lower_map:
            continue
        if len(tok) >= 4:
            matches = difflib.get_close_matches(tok.lower(), vocab_lower_map.keys(), n=1, cutoff=0.75)
            if matches:
                expansions.append(vocab_lower_map[matches[0]])
    if expansions:
        deduped = " ".join(dict.fromkeys(expansions))
        return query + " [Auto-expanded: " + deduped + "]"
    return query


# Backward-compatible aliases (historical names in tests / query shim)
_is_noise_stem = is_noise_stem
_load_symbols_vocab = load_symbols_vocab
_god_mode_chunk_name_matches = god_mode_chunk_name_matches
_expand_query_typos = expand_query_typos
