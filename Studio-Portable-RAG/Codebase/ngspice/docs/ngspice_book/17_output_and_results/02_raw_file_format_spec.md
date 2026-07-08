---
title: "Raw file format"
chapter: "17_output_and_results"
section: "02_raw_file_format_spec"
section_number: "17.2"
topic: "02_raw_file_format_spec"
mission_primary: "circuit_design_validation"
mission_secondary: []
related_files:
  - "src/frontend/rawfile.c"
related_chapters:
  - "../23_canonical_chains_reference/10_raw_output_consumption_chain.md"
domain_concepts:
  - "raw_format"
canonical_chain_tags:
  - "raw_output_consumption_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 10
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Raw file format {#raw-file-format}

## Writer entry point {#writer}

`raw_write` opens the destination file, decides precision, and refuses to serialize empty plots ([Source: src/frontend/rawfile.c#L34-L57]).

## ASCII vs binary {#ascii-vs-binary}

The `binary` flag selects compact binary encoding; padding can be suppressed via the `nopadding` variable ([Source: src/frontend/rawfile.c#L51]).

## Consumer guidance {#consumer}

Downstream tools should mirror ngspice’s header parsing (variables block, plot metadata, then column-major data) exactly as emitted here—`PySpice` and similar wrappers depend on this layout ([Source: ../17_output_and_results/06_consuming_raw_with_pyspice.md]).
