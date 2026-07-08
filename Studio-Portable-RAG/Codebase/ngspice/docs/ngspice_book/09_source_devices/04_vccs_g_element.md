---
title: "VCCS (G)"
chapter: "09_source_devices"
section: "04_vccs_g_element"
section_number: "9.4"
topic: "04_vccs_g_element"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/spicelib/devices/vccs/vccsload.c"
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
estimated_reading_minutes: 5
last_updated_from_source_at: "2026-04-09T03:39:07.072860+00:00"
---

# VCCS (G) {#vccs-g-element}

## Overview {#overview}

`VCCSload` implements a voltage-controlled current source as off-diagonal conductance stamps between controlling and controlled nodes ([Source: src/spicelib/devices/vccs/vccsload.c#L33-L37]).

<!-- source: src/spicelib/devices/vccs/vccsload.c -->

## Source Files {#source-files}

- **`src/spicelib/devices/vccs/vccsload.c`**

## Related Chapters {#related-chapters}

- [VCVS](03_vcvs_e_element.md)
