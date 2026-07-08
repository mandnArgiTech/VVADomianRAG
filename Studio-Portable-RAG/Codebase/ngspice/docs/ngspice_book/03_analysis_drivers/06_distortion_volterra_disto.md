---
title: "Distortion (DISTOan)"
chapter: "03_analysis_drivers"
section: "06_distortion_volterra_disto"
section_number: "3.6"
topic: "06_distortion_volterra_disto"
mission_primary: "kernel_reimplementation"
mission_secondary: ["circuit_design_validation"]
related_files:
  - "src/spicelib/analysis/distoan.c"
related_chapters:
  - "../14_netlist_grammar/07_dot_noise_dot_disto.md"
domain_concepts:
  - "distortion_analysis"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 8
last_updated_from_source_at: "2026-04-09T03:39:07.072860+00:00"
---

# Distortion (DISTOan) {#distortion-volterra-disto}

## Overview {#overview}

`DISTOan` performs small-signal distortion analysis using the Volterra-series machinery (`distodef.h`). The entry point allocates auxiliary storage (`DmemAlloc`, `DstorAlloc`) and iterates frequency points similar to AC analysis ([Source: src/spicelib/analysis/distoan.c#L22-L49]).

<!-- source: src/spicelib/analysis/distoan.c -->

## Source Files {#source-files}

- **`src/spicelib/analysis/distoan.c`**

## Related Chapters {#related-chapters}

- [.noise / .disto grammar](../14_netlist_grammar/07_dot_noise_dot_disto.md)
