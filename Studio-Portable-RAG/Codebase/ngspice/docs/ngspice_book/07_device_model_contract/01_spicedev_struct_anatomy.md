---
title: "SPICEdev struct anatomy"
chapter: "07_device_model_contract"
section: "01_spicedev_struct_anatomy"
section_number: "7.1"
topic: "01_spicedev_struct_anatomy"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/include/ngspice/devdefs.h"
  - "src/spicelib/devices/bsim4/bsim4init.c"
related_chapters:
  - "../01_architecture_overview/03_spicedev_plugin_contract.md"
  - "03_devload_load_function.md"
domain_concepts:
  - "device_model_contract"
canonical_chain_tags:
  - "device_load_dispatch_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 12
last_updated_from_source_at: "2026-04-09T03:39:07.065678+00:00"
---

# SPICEdev struct anatomy {#spicedev-struct-anatomy}

## Overview {#overview}

`SPICEdev` pairs human-facing metadata (`IFdevice DEVpublic`) with the full vtable of simulator callbacks—parameter IO, matrix loads, AC linearizations, truncation, sensitivity, noise, destruction, etc. ([Source: src/include/ngspice/devdefs.h#L47-L117]).

Concrete wiring for a complex MOSFET model appears in `BSIM4info`, where each slot is bound to a function symbol (`BSIM4load`, `BSIM4acLoad`, `BSIM4trunc`, …) ([Source: src/spicelib/devices/bsim4/bsim4init.c#L10-L77]).

<!-- source: src/include/ngspice/devdefs.h -->
<!-- source: src/spicelib/devices/bsim4/bsim4init.c -->

## Field Groups {#field-groups}

| Group | Callbacks | Role |
|-------|-----------|------|
| Parameterization | `DEVparam`, `DEVmodParam` | Instance/model card parsing |
| Core stamping | `DEVload`, `DEVacLoad`, `DEVpzLoad` | Resistive, AC, pole-zero Jacobians |
| Time domain | `DEVtrunc`, `DEVaccept` | LTE estimates, accepted-step hooks |
| Newton assistance | `DEVconvTest` | Extra convergence checks |
| Physics setup | `DEVsetup`, `DEVtemperature`, `DEVsetic` | Precomputation, temp dependence, initial guesses |
| Lifecycle | `DEVdestroy`, `DEVdelete`, `DEVmodDelete` | Tear-down |
| Advanced | `DEVnoise`, `DEVdisto`, `DEVsen*` | Noise, distortion, sensitivity |

([Source: src/include/ngspice/devdefs.h#L50-L105])

## Example: BSIM4 Table {#bsim4-example}

BSIM4 populates nearly every critical slot: `BSIM4load`, `BSIM4acLoad`, `BSIM4trunc`, `BSIM4convTest`, `BSIM4noise`, `BSIM4soaCheck`, while leaving unused hooks `NULL` ([Source: src/spicelib/devices/bsim4/bsim4init.c#L43-L70]).

## Source Files {#source-files}

- **`src/include/ngspice/devdefs.h`**
- **`src/spicelib/devices/bsim4/bsim4init.c`** — reference implementation of a filled `SPICEdev`.

## Related Chapters {#related-chapters}

- [Plugin contract](../01_architecture_overview/03_spicedev_plugin_contract.md)
- [DEVload](03_devload_load_function.md)
