---
title: "DevParam parameter handling"
chapter: "07_device_model_contract"
section: "02_devparam_parameter_handling"
section_number: "7.2"
topic: "02_devparam_parameter_handling"
mission_primary: "kernel_reimplementation"
mission_secondary: ["circuit_design_validation"]
related_files:
  - "src/include/ngspice/devdefs.h"
  - "src/spicelib/devices/bsim4/bsim4init.c"
related_chapters:
  - "../14_netlist_grammar/02_device_card_grammar.md"
  - "01_spicedev_struct_anatomy.md"
domain_concepts:
  - "device_model_contract"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 8
last_updated_from_source_at: "2026-04-09T03:39:07.065678+00:00"
---

# DevParam parameter handling {#devparam-parameter-handling}

## Overview {#overview}

Device parameters are described twice: (1) at the C API level via `DEVparam` / `DEVmodParam` function pointers inside `SPICEdev`, and (2) in the `IFdevice` metadata (`pTable`, `mPTable`, …) that names parameters for the front-end ([Source: src/include/ngspice/devdefs.h#L47-L55], [Source: src/spicelib/devices/bsim4/bsim4init.c#L19-L23]).

BSIM4 binds `BSIM4param` to `DEVparam` and `BSIM4mParam` to `DEVmodParam` ([Source: src/spicelib/devices/bsim4/bsim4init.c#L43-L44]).

<!-- source: src/include/ngspice/devdefs.h -->
<!-- source: src/spicelib/devices/bsim4/bsim4init.c -->

## What This Section Does {#what-it-does}

Separates *instance* parameters (per transistor) from *model* parameters (shared `.model` card) at the vtable level—both must be implemented for a complete device.

## IOP Macros {#iop-macros}

`devdefs.h` defines extensive macros (`IOP`, `IOPP`, `IOPA`, …) that expand into `IFparm` initializer entries with the correct `IF_SET` / `IF_ASK` / `IF_AC` flags for each query surface ([Source: src/include/ngspice/devdefs.h#L124-L163]).

## Source Files {#source-files}

- **`src/include/ngspice/devdefs.h`**
- **`src/spicelib/devices/bsim4/bsim4init.c`** — exemplary `IFdevice` tables.

## Related Chapters {#related-chapters}

- [Device card grammar](../14_netlist_grammar/02_device_card_grammar.md)
- [SPICEdev anatomy](01_spicedev_struct_anatomy.md)
