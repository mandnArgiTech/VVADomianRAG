"""Chunk sizing and domain constants shared by ingestion."""

# Target max tokens per chunk for RFC splitting (char budget ~= tokens * 4).
MODEL_TOKEN_LIMITS = {
    "mxbai-embed-large": 512,
    "nomic-embed-text": 8192,
}
DEFAULT_RFC_TOKEN_LIMIT = 512

MIB_MODULE_CONCEPTS = {
    "BRIDGE-MIB": "stp,forwarding_table",
    "IF-MIB": "interface_management",
    "Q-BRIDGE-MIB": "vlan",
    "LLDP-MIB": "lldp",
}
