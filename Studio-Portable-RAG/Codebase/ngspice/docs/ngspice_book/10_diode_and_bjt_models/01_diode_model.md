---
title: "Diode model"
chapter: "10_diode_and_bjt_models"
section: "01_diode_model"
section_number: "10.1"
topic: "01_diode_model"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/spicelib/devices/dio/dioload.c"
related_chapters:
  - "../02_numerical_kernel_core/05_voltage_limiting_devpnjlim.md"
domain_concepts:
  - "device_model_contract"
canonical_chain_tags:
  - "device_load_dispatch_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 8
last_updated_from_source_at: "2026-04-09T03:39:07.072860+00:00"
---

# Diode model {#diode-model}

## Overview {#overview}

`DIOload` implements the full DC, charge, and conductance equations for the SPICE diode. Before evaluating exponentials it passes trial voltages through `DEVpnjlim`, including a specialized breakdown path when `DIObreakdownVoltage` is specified ([Source: src/spicelib/devices/dio/dioload.c#L183-L194]).

<!-- source: src/spicelib/devices/dio/dioload.c -->

## Source Files {#source-files}

- **`src/spicelib/devices/dio/dioload.c`**

## Related Chapters {#related-chapters}

- [DEVpnjlim](../02_numerical_kernel_core/05_voltage_limiting_devpnjlim.md)
