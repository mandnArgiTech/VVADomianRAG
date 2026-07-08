---
title: "CCVS (H)"
chapter: "09_source_devices"
section: "05_ccvs_h_element"
section_number: "9.5"
topic: "05_ccvs_h_element"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/spicelib/devices/ccvs/ccvsload.c"
related_chapters:
  - "03_vcvs_e_element.md"
domain_concepts:
  - "mna_modified_nodal_analysis"
canonical_chain_tags:
  - "device_load_dispatch_chain"
numerical_invariants_introduced:
  - "mna_matrix_assembly"
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 6
last_updated_from_source_at: "2026-04-09T03:39:07.072860+00:00"
---

# CCVS (H) {#ccvs-h-element}

## Overview {#overview}

`CCVSload` ties a branch voltage to a sensed branch current via extra matrix entries on the controlling branch column ([Source: src/spicelib/devices/ccvs/ccvsload.c#L35-L39]).

<!-- source: src/spicelib/devices/ccvs/ccvsload.c -->

## Source Files {#source-files}

- **`src/spicelib/devices/ccvs/ccvsload.c`**

## Related Chapters {#related-chapters}

- [VCVS](03_vcvs_e_element.md)
