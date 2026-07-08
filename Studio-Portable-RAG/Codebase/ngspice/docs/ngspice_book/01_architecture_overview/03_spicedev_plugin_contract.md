---
title: "SPICEdev plugin contract"
chapter: "01_architecture_overview"
section: "03_spicedev_plugin_contract"
section_number: "1.3"
topic: "03_spicedev_plugin_contract"
mission_primary: "kernel_reimplementation"
mission_secondary: ["circuit_design_validation"]
related_files:
  - "src/include/ngspice/devdefs.h"
  - "src/spicelib/devices/dev.c"
related_chapters:
  - "../07_device_model_contract/01_spicedev_struct_anatomy.md"
  - "../01_architecture_overview/04_function_pointer_dispatch.md"
domain_concepts:
  - "device_model_contract"
canonical_chain_tags:
  - "device_load_dispatch_chain"
numerical_invariants_introduced: []
glossary_terms_introduced:
  - "SPICEdev"
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 12
last_updated_from_source_at: "2026-04-09T03:39:07.065678+00:00"
---

# SPICEdev plugin contract {#spicedev-plugin-contract}

## Overview {#overview}

Every device family (resistor, MOS, VCVS, …) packages its behavior behind a `SPICEdev` structure: a public `IFdevice` descriptor plus function pointers for loading (`DEVload`), AC stamping (`DEVacLoad`), truncation (`DEVtrunc`), convergence tests (`DEVconvTest`), noise (`DEVnoise`), sensitivity hooks, and lifecycle (`DEVsetup`, `DEVunsetup`, `DEVdelete`, …) ([Source: src/include/ngspice/devdefs.h#L47-L117]).

At startup, `spice_init_devices` fills the global `DEVices[]` table by calling each static factory in `static_devices[]` ([Source: src/spicelib/devices/dev.c#L247-L265]).

<!-- source: src/include/ngspice/devdefs.h -->
<!-- source: src/spicelib/devices/dev.c -->

## What This Section Does {#what-it-does}

Explains why adding a model means implementing a *table* of callbacks, not a single equation file. Chapter 7 enumerates each callback with file-level references.

## Mandatory vs Optional Methods {#mandatory}

`CKTload` only requires `DEVload` to be non-NULL for a type to participate in resistive stamping ([Source: src/spicelib/analysis/cktload.c#L61-L63]). Other analyses consult their respective hooks (`DEVacLoad`, `DEVtrunc`, …) when those subsystems run.

## Dynamic Extensibility {#dynamic}

`DEVices` and `DEVmaxnum` are globals; XSPICE may extend the table at runtime ([Source: src/include/ngspice/devdefs.h#L120-L121], [Source: src/spicelib/devices/dev.c#L365-L376] for `TREALLOC` path).

## Source Files {#source-files}

- **`src/include/ngspice/devdefs.h`** — `SPICEdev` typedef and `DEVices` externs.
- **`src/spicelib/devices/dev.c`** — `spice_init_devices`, `devices()` accessor.

## Related Chapters {#related-chapters}

- [SPICEdev struct anatomy](../07_device_model_contract/01_spicedev_struct_anatomy.md)
- [Function pointer dispatch](04_function_pointer_dispatch.md)

## Canonical Chains {#canonical-chains}

- `device_load_dispatch_chain`

## Glossary {#glossary}

- **SPICEdev** — Device vtable + metadata; see [Device modeling terms](../24_glossary/02_device_modeling_terms.md#device-modeling-terms).
