---
title: "Writing a new device model"
chapter: "07_device_model_contract"
section: "11_writing_a_new_device_model"
section_number: "7.11"
topic: "11_writing_a_new_device_model"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/include/ngspice/devdefs.h"
  - "src/spicelib/devices/dev.c"
  - "src/spicelib/devices/bsim4/bsim4init.c"
related_chapters:
  - "01_spicedev_struct_anatomy.md"
  - "../01_architecture_overview/03_spicedev_plugin_contract.md"
domain_concepts:
  - "device_model_contract"
canonical_chain_tags:
  - "device_load_dispatch_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "ngspice core developer"
estimated_reading_minutes: 10
last_updated_from_source_at: "2026-04-09T03:39:07.104114+00:00"
---

# Writing a new device model {#writing-a-new-device-model}

## Overview {#overview}

A new elementary device is a new `SPICEdev` instance plus registration in `static_devices[]` so `spice_init_devices` picks it up ([Source: src/spicelib/devices/dev.c#L247-L265]). The BSIM4 source tree is the canonical pattern: define parameter tables, implement `DEVload` / `DEVsetup` / `DEVacLoad` / `DEVtrunc` as needed, then aggregate them in an `SPICEdev` literal ([Source: src/spicelib/devices/bsim4/bsim4init.c#L10-L77]).

<!-- source: src/include/ngspice/devdefs.h -->
<!-- source: src/spicelib/devices/dev.c -->
<!-- source: src/spicelib/devices/bsim4/bsim4init.c -->

## Checklist {#checklist}

1. **Metadata** — Fill `IFdevice` name, description, parameter tables ([Source: src/spicelib/devices/bsim4/bsim4init.c#L10-L23]).
2. **Core physics** — Implement `DEVload` with limiting helpers from `devsup.c` when exponentials appear.
3. **AC / noise / trunc** — Wire optional analyses; use `NULL` when unsupported (BSIM4 example, [Source: src/spicelib/devices/bsim4/bsim4init.c#L51-L67]).
4. **Lifecycle** — Provide `DEVdestroy`, `DEVdelete`, `DEVmodDelete` to free model graphs.
5. **Registration** — Append factory to `static_devices` in `dev.c` so `DEVices[i]` resolves at runtime.

## Source Files {#source-files}

- **`src/include/ngspice/devdefs.h`** — contract reference.
- **`src/spicelib/devices/dev.c`** — device table bootstrap.
- **`src/spicelib/devices/bsim4/bsim4init.c`** — worked example.

## Related Chapters {#related-chapters}

- [SPICEdev anatomy](01_spicedev_struct_anatomy.md)
- [Plugin overview](../01_architecture_overview/03_spicedev_plugin_contract.md)
