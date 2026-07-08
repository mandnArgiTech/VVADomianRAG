---
title: "Resistor"
chapter: "08_passive_devices"
section: "01_resistor"
section_number: "8.1"
topic: "01_resistor"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/spicelib/devices/res/resload.c"
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
estimated_reading_minutes: 6
last_updated_from_source_at: "2026-04-09T03:39:07.072860+00:00"
---

# Resistor {#resistor}

## Overview {#overview}

`RESload` stamps a symmetric 2×2 conductance matrix using the precomputed `RESconduct` field and optional multiplier `RESm` ([Source: src/spicelib/devices/res/resload.c#L16-L38]). Branch current for diagnostics uses the voltage drop times conductance ([Source: src/spicelib/devices/res/resload.c#L29-L30]).

`RESacload` duplicates the stamp for AC unless an AC-specific resistance was provided ([Source: src/spicelib/devices/res/resload.c#L47-L70]).

<!-- source: src/spicelib/devices/res/resload.c -->

## Source Files {#source-files}

- **`src/spicelib/devices/res/resload.c`**

## Related Chapters {#related-chapters}

- [CKTload dispatch](../02_numerical_kernel_core/01_circuit_load_dispatch_cktload.md)
