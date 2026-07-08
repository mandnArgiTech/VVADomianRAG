---
title: "Independent voltage source"
chapter: "09_source_devices"
section: "01_independent_voltage_source"
section_number: "9.1"
topic: "01_independent_voltage_source"
mission_primary: "kernel_reimplementation"
mission_secondary: ["circuit_design_validation"]
related_files:
  - "src/spicelib/devices/vsrc/vsrcload.c"
related_chapters:
  - "../02_numerical_kernel_core/01_circuit_load_dispatch_cktload.md"
domain_concepts:
  - "mna_modified_nodal_analysis"
canonical_chain_tags:
  - "device_load_dispatch_chain"
numerical_invariants_introduced:
  - "mna_matrix_assembly"
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 8
last_updated_from_source_at: "2026-04-09T03:39:07.072860+00:00"
---

# Independent voltage source {#independent-voltage-source}

## Overview {#overview}

`VSRCload` stamps the branch equations for a voltage source (identity ties between branch current and nodal KCL) and selects the enforced voltage from DC, transient, or piecewise functions ([Source: src/spicelib/devices/vsrc/vsrcload.c#L43-L67]).

During DC operating point / DC sweep, `VSRCdcValue` scales by `ckt->CKTsrcFact` unless XSPICE extensions alter that path ([Source: src/spicelib/devices/vsrc/vsrcload.c#L47-L55]).

<!-- source: src/spicelib/devices/vsrc/vsrcload.c -->

## Source Files {#source-files}

- **`src/spicelib/devices/vsrc/vsrcload.c`**

## Related Chapters {#related-chapters}

- [CKTload dispatch](../02_numerical_kernel_core/01_circuit_load_dispatch_cktload.md)
