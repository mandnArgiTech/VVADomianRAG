#!/usr/bin/env python3
"""Validate rag_index.json structure and canonical_chain_tags."""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REQUIRED_FILE_KEYS = frozenset(
    {
        "path",
        "file_id",
        "category",
        "language",
        "loc",
        "sloc_total",
        "size_bytes",
        "content_hash",
        "last_modified",
        "job_relevance",
        "numerical_invariant_kind",
        "numerical_constants_defined",
        "device_model_kind",
        "spicedev_function_implemented",
        "spice_analysis_role",
        "circuit_designer_topic",
        "module",
        "subsystem",
        "header_pair",
        "device_family_directory",
        "c_includes_internal",
        "key_functions_defined",
        "summary",
        "purpose",
        "domain_concepts",
        "tags",
        "key_symbols",
        "imports_internal",
        "imports_external",
        "imported_by",
        "imported_by_count",
        "call_graph_outgoing",
        "function_pointer_tables_referenced",
        "chunking_strategy",
        "max_chunk_tokens",
        "chunk_overlap_tokens",
        "preserve_together",
        "importance_score",
        "query_hints",
        "related_files",
        "canonical_chain_tags",
        "notes",
    }
)


def main() -> int:
    path = REPO / "rag_index.json"
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
    data = json.loads(path.read_text(encoding="utf-8"))
    errors: list[str] = []

    chain_ids = {c["chain_id"] for c in data.get("canonical_chains", [])}
    indexed = {f["path"] for f in data["files"]}

    for c in data.get("canonical_chains", []):
        for m in c.get("canonical_members", []):
            if "<" in m:
                continue
            if m not in indexed:
                errors.append(f"canonical_members not indexed: {m} (chain {c['chain_id']})")

    for i, f in enumerate(data["files"]):
        missing = REQUIRED_FILE_KEYS - f.keys()
        if missing:
            errors.append(f"{f.get('path', i)}: missing keys {sorted(missing)}")
        jr = f.get("job_relevance", {})
        for k in ("kernel_reimplementation", "circuit_design_validation"):
            if k not in jr:
                errors.append(f"{f['path']}: bad job_relevance")
        for tag in f.get("canonical_chain_tags", []):
            if tag not in chain_ids:
                errors.append(f"{f['path']}: unknown canonical_chain_tag {tag}")

    st = data.get("stats", {})
    if st.get("files_included") != len(data["files"]):
        errors.append(
            f"stats.files_included {st.get('files_included')} != len(files) {len(data['files'])}"
        )
    if st.get("total_canonical_chains") != len(data.get("canonical_chains", [])):
        errors.append("stats.total_canonical_chains mismatch")

    m = st.get("breakdown_by_mission_relevance", {})
    s = sum(m.values())
    if s != len(data["files"]):
        errors.append(
            f"mission_relevance sum {s} != files {len(data['files'])}: {m}"
        )

    if errors:
        print("VALIDATION FAILED:", file=sys.stderr)
        for e in errors[:50]:
            print(f"  {e}", file=sys.stderr)
        if len(errors) > 50:
            print(f"  ... and {len(errors) - 50} more", file=sys.stderr)
        return 1
    print(
        f"OK: {len(data['files'])} files, "
        f"{len(data.get('canonical_chains', []))} chains, "
        f"{len(data.get('groups', []))} groups"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
