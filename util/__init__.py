"""Utility modules for DomainRAG.

Submodules
----------
constants        DIM_TO_MODEL, LANG_TAG
chroma_client    Chroma connection, embedding detection, collection discovery
formatting       infer_source_type, truncate_chunk, format_result, format_markdown…
chunk_metadata   metadata_pipe_or_comma_tokens, depend_stems_from_results…
search_core      SearchHit, sync_multi_search, sync_multi_search_with_dependency_hop…
universal_vision_parser   PDF vision parsing
"""

__all__: list[str] = [
    "constants",
    "chroma_client",
    "formatting",
    "chunk_metadata",
    "search_core",
    "universal_vision_parser",
]
