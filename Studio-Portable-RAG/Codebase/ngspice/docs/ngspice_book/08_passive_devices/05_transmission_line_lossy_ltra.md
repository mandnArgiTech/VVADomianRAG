---
title: "Lossy transmission line (LTRA)"
chapter: "08_passive_devices"
section: "05_transmission_line_lossy_ltra"
section_number: "8.5"
topic: "05_transmission_line_lossy_ltra"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/spicelib/devices/ltra/ltraload.c"
related_chapters:
  - "04_transmission_line_lossless_tra.md"
domain_concepts:
  - "mna_modified_nodal_analysis"
canonical_chain_tags:
  - "transient_step_chain"
numerical_invariants_introduced:
  - "mna_matrix_assembly"
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 8
last_updated_from_source_at: "2026-04-09T03:39:07.072860+00:00"
---

# Lossy transmission line (LTRA) {#transmission-line-lossy-ltra}

## Overview {#overview}

`LTRAload` is substantially more elaborate than `TRAload`: it branches on `CKTmode` (e.g., pure DC `MODEDC` shortcuts) and maintains internal delayed histories for lossy telegrapher equations ([Source: src/spicelib/devices/ltra/ltraload.c#L13-L45]).

<!-- source: src/spicelib/devices/ltra/ltraload.c -->

## Source Files {#source-files}

- **`src/spicelib/devices/ltra/ltraload.c`**

## Related Chapters {#related-chapters}

- [Lossless TRA](04_transmission_line_lossless_tra.md)
