"""
MCP-facing entry for single-file domain markdown ingest.

Re-exports ``feed_domain_document`` from ``ingest`` so callers avoid dynamic
importlib loading while keeping a small, explicit integration surface.
"""

from ingest import feed_domain_document

__all__ = ["feed_domain_document"]
