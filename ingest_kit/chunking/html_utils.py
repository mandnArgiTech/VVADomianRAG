"""HTML stripping for ticket/wiki text."""

from __future__ import annotations

import re

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover
    BeautifulSoup = None  # type: ignore


def strip_html(text: str) -> str:
    if BeautifulSoup is not None:
        return BeautifulSoup(text, "html.parser").get_text("\n")
    return re.sub(r"<[^>]+>", " ", text)
