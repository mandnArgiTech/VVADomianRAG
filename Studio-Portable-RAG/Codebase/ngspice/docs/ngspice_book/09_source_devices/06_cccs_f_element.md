---
title: "CCCS (F)"
chapter: "09_source_devices"
section: "06_cccs_f_element"
section_number: "9.6"
topic: "06_cccs_f_element"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/spicelib/devices/cccs/cccsload.c"
related_chapters:
  - "05_ccvs_h_element.md"
domain_concepts:
  - "mna_modified_nodal_analysis"
canonical_chain_tags:
  - "device_load_dispatch_chain"
numerical_invariants_introduced:
  - "mna_matrix_assembly"
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 5
last_updated_from_source_at: "2026-04-09T03:39:07.072860+00:00"
---

# CCCS (F) {#cccs-f-element}

## Overview {#overview}

`CCCSload` injects a current proportional to a reference branch current by stamping coefficients on the branch rows ([Source: src/spicelib/devices/cccs/cccsload.c#L35-L36]).

<!-- source: src/spicelib/devices/cccs/cccsload.c -->

## Source Files {#source-files}

- **`src/spicelib/devices/cccs/cccsload.c`**

## Related Chapters {#related-chapters}

- [CCVS](05_ccvs_h_element.md)
