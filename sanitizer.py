"""sanitizer.py — PII removal for customer ticket ingestion."""

import re

DEFAULT_PATTERNS = [
    (r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(/\d{1,2})?\b", "x.x.x.x"),
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "[email]"),
    (r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", "[phone]"),
    (r"\b([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b", "[mac]"),
    # Hostnames: require subdomain.domain.tld (3+ labels) to avoid ieee802.1d, layer2.forwarding, etc.
    (
        r"\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.){2,}[a-zA-Z]{2,}\b",
        "[hostname]",
    ),
]


def sanitize(
    text: str,
    extra_patterns: list = None,
    company_names: list = None,
) -> str:
    """Remove PII from text. company_names is a list of strings to redact."""
    if not text:
        return text
    for pattern, replacement in DEFAULT_PATTERNS + (extra_patterns or []):
        text = re.sub(pattern, replacement, text)
    for name in company_names or []:
        if name and name.strip():
            text = re.sub(re.escape(name.strip()), "[customer]", text, flags=re.IGNORECASE)
    return text
