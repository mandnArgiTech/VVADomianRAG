---
title: "Simple transmission line (TXL)"
chapter: "08_passive_devices"
section: "06_transmission_line_simple_txl"
section_number: "8.6"
topic: "06_transmission_line_simple_txl"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/spicelib/devices/txl/txlload.c"
related_chapters:
  - "05_transmission_line_lossy_ltra.md"
domain_concepts:
  - "mna_modified_nodal_analysis"
canonical_chain_tags:
  - "transient_step_chain"
numerical_invariants_introduced:
  - "mna_matrix_assembly"
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 7
last_updated_from_source_at: "2026-04-09T03:39:07.072860+00:00"
---

# Simple transmission line (TXL) {#transmission-line-simple-txl}

## Overview {#overview}

`TXLload` implements the TXL macromodel with internal delay buffers (`TXLine` structures) and helper routines for updating traveling-wave quantities ([Source: src/spicelib/devices/txl/txlload.c#L14-L40]).

<!-- source: src/spicelib/devices/txl/txlload.c -->

## Source Files {#source-files}

- **`src/spicelib/devices/txl/txlload.c`**

## Related Chapters {#related-chapters}

- [LTRA](05_transmission_line_lossy_ltra.md)
