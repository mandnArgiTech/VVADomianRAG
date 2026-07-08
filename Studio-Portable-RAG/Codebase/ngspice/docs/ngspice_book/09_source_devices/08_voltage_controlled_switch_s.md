---
title: "Voltage-controlled switch (S)"
chapter: "09_source_devices"
section: "08_voltage_controlled_switch_s"
section_number: "9.8"
topic: "08_voltage_controlled_switch_s"
mission_primary: "kernel_reimplementation"
mission_secondary: ["circuit_design_validation"]
related_files:
  - "src/spicelib/devices/sw/swload.c"
related_chapters:
  - "../04_convergence_aids/06_convergence_failure_diagnosis.md"
domain_concepts:
  - "piecewise_linear_devices"
canonical_chain_tags:
  - "device_load_dispatch_chain"
numerical_invariants_introduced:
  - "mna_matrix_assembly"
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 7
last_updated_from_source_at: "2026-04-09T03:39:07.072860+00:00"
---

# Voltage-controlled switch (S) {#voltage-controlled-switch-s}

## Overview {#overview}

`SWload` reads the control voltage from `CKTrhsOld`, tracks hysteresis state in dedicated state slots, and stamps a conductance `g_now` between the switched terminals ([Source: src/spicelib/devices/sw/swload.c#L23-L48]).

<!-- source: src/spicelib/devices/sw/swload.c -->

## Source Files {#source-files}

- **`src/spicelib/devices/sw/swload.c`**

## Related Chapters {#related-chapters}

- [Convergence diagnosis](../04_convergence_aids/06_convergence_failure_diagnosis.md)
