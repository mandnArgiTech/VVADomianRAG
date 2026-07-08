---
title: "VCVS (E)"
chapter: "09_source_devices"
section: "03_vcvs_e_element"
section_number: "9.3"
topic: "03_vcvs_e_element"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/spicelib/devices/vcvs/vcvsload.c"
related_chapters:
  - "01_independent_voltage_source.md"
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

# VCVS (E) {#vcvs-e-element}

## Overview {#overview}

`VCVSload` stamps the controlled voltage source: branch KCL ties plus control coefficients on the sense nodes ([Source: src/spicelib/devices/vcvs/vcvsload.c#L33-L39]).

<!-- source: src/spicelib/devices/vcvs/vcvsload.c -->

## Source Files {#source-files}

- **`src/spicelib/devices/vcvs/vcvsload.c`**

## Related Chapters {#related-chapters}

- [Independent voltage source](01_independent_voltage_source.md)
