---
title: "Consuming raw with PySpice"
chapter: "17_output_and_results"
section: "06_consuming_raw_with_pyspice"
section_number: "17.6"
topic: "06_consuming_raw_with_pyspice"
mission_primary: "circuit_design_validation"
mission_secondary: []
related_files:
  - "src/frontend/rawfile.c"
related_chapters:
  - "../17_output_and_results/02_raw_file_format_spec.md"
domain_concepts:
  - "pyspice_raw"
canonical_chain_tags:
  - "raw_output_consumption_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 8
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Consuming raw with PySpice {#consuming-raw-with-pyspice}

## Contract {#contract}

PySpice and similar tools parse the same ASCII/binary headers `raw_write` emits; keep ngspice on default padding/precision unless your parser explicitly handles variants ([Source: src/frontend/rawfile.c#L34-L57]).

## Workflow {#workflow}

1. Run ngspice with `write my.raw` or `-r my.raw`.
2. Load via PySpice `SpiceRawLibrary` (or pandas conversion).
3. Verify the **scale vector** (`time`, `frequency`, sweep variable) matches expectations—multi-step analyses append multiple plots.

## Pitfalls {#pitfalls}

- Mixed real/complex plots (AC) require interpreting `VF_COMPLEX` metadata mirrored from `dvec` ([Source: src/include/ngspice/dvec.h#L8-L18]).
