---
title: "Current-controlled switch (W)"
chapter: "09_source_devices"
section: "09_current_controlled_switch_w"
section_number: "9.9"
topic: "09_current_controlled_switch_w"
mission_primary: "kernel_reimplementation"
mission_secondary: ["circuit_design_validation"]
related_files:
  - "src/spicelib/devices/csw/cswload.c"
related_chapters:
  - "08_voltage_controlled_switch_s.md"
domain_concepts:
  - "piecewise_linear_devices"
canonical_chain_tags:
  - "device_load_dispatch_chain"
numerical_invariants_introduced:
  - "mna_matrix_assembly"
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 6
last_updated_from_source_at: "2026-04-09T03:39:07.072860+00:00"
---

# Current-controlled switch (W) {#current-controlled-switch-w}

## Overview {#overview}

`CSWload` mirrors `SWload` but senses a branch current (`CKTrhsOld` indexed by `CSWcontBranch`) instead of a control voltage difference ([Source: src/spicelib/devices/csw/cswload.c#L40-L44]).

<!-- source: src/spicelib/devices/csw/cswload.c -->

## Source Files {#source-files}

- **`src/spicelib/devices/csw/cswload.c`**

## Related Chapters {#related-chapters}

- [Voltage-controlled switch](08_voltage_controlled_switch_s.md)
