---
title: "Handling indirect dispatch in Python"
chapter: "22_nodalai_kernel_reimplementation"
section: "06_handling_indirect_dispatch_in_python"
section_number: "22.6"
topic: "handling_indirect_dispatch_in_python"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/include/ngspice/devdefs.h"
  - "src/spicelib/analysis/cktload.c"
  - "src/spicelib/devices/dev.c"
related_chapters:
  - "../01_architecture_overview/04_function_pointer_dispatch.md"
  - "../07_device_model_contract/01_spicedev_struct_anatomy.md"
domain_concepts:
  - "device_dispatch"
canonical_chain_tags:
  - "device_load_dispatch_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 9
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Handling indirect dispatch in Python {#handling-indirect-dispatch-in-python}

## What C does {#what-c-does}

`CKTload` indexes a global `DEVices[]` array and calls the non-NULL `DEVload` for each model list head ([Source: src/spicelib/analysis/cktload.c#L61-L74]). Each entry is a `SPICEdev` describing metadata and function pointers ([Source: src/include/ngspice/devdefs.h#L47-L117]).

## Python patterns {#patterns}

- **Registry dict:** `DEVICE_LOADERS["resistor"] = load_resistor` keyed by the same enumeration order you assign internally.
- **Single dispatch:** Methods on a `Device` base class; optional `functools.singledispatch` for instance data shapes.
- **JIT / codegen:** For performance, generate one fused `load_all` after netlist elaboration—mirrors what static C achieves via monomorphization.

## Registration time {#registration}

ngspice binds devices during startup via `dev.c` tables; Python ports should separate **registration** (schema) from **instance binding** (per netlist) to match that two-phase pattern ([Source: ../01_architecture_overview/03_spicedev_plugin_contract.md]).
