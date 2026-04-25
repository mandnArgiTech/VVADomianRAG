"""Utility modules for VVADomainRAG.

Submodules
----------
constants          Shared constants (DIM_TO_MODEL, LANG_TAG, env tunables)
chroma_client      Chroma connection, embedding detection, collection discovery
formatting         Chunk and result formatting (format_result, format_markdown …)
chunk_metadata     Metadata token splitting, dependency-hop filter building
search_primitives  SearchHit dataclass, collection routing, dense search helpers
universal_vision_parser   PDF vision parsing
"""

__all__ = [
    "constants",
    "chroma_client",
    "formatting",
    "chunk_metadata",
    "search_primitives",
    "universal_vision_parser",
]
