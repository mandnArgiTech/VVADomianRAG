---
title: "Independent current source"
chapter: "09_source_devices"
section: "02_independent_current_source"
section_number: "9.2"
topic: "02_independent_current_source"
mission_primary: "kernel_reimplementation"
mission_secondary: ["circuit_design_validation"]
related_files:
  - "src/spicelib/devices/isrc/isrcload.c"
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
estimated_reading_minutes: 7
last_updated_from_source_at: "2026-04-09T03:39:07.072860+00:00"
---

# Independent current source {#independent-current-source}

## Overview {#overview}

`ISRCload` parallels `VSRCload`: DC values honor `CKTsrcFact` when not in the XSPICE-expanded branch, while transient waveforms evaluate at `ckt->CKTtime` ([Source: src/spicelib/devices/isrc/isrcload.c#L46-L60]).

<!-- source: src/spicelib/devices/isrc/isrcload.c -->

## Source Files {#source-files}

- **`src/spicelib/devices/isrc/isrcload.c`**

## Related Chapters {#related-chapters}

- [Voltage source](01_independent_voltage_source.md)
