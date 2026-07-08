---
title: "Raw file output chain"
chapter: "23_canonical_chains_reference"
section: "10_raw_output_consumption_chain"
section_number: "23.10"
topic: "raw_output_consumption_chain"
mission_primary: "circuit_design_validation"
mission_secondary: []
related_files:
  - "src/frontend/rawfile.c"
related_chapters:
  - "../17_output_and_results/02_raw_file_format_spec.md"
domain_concepts:
  - "raw_file"
canonical_chain_tags:
  - "raw_output_consumption_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 7
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Raw file output chain {#raw-output-consumption-chain}

## Summary {#summary}

`raw_write` serializes the active `plot` (vectors, dimensions, ASCII vs binary) to a named file, skipping empty plots ([Source: src/frontend/rawfile.c#L34-L57]). This is the bridge between in-memory `dvec` results and external tools.

## Stages {#stages}

`sim_complete` → `raw_serialize` ([Source: rag_index.json]).

## Canonical members {#members}

`src/frontend/rawfile.c`

## Deep dives {#deep-dives}

- [Raw format](../17_output_and_results/02_raw_file_format_spec.md)
