---
title: "HiSIM-HV"
chapter: "11_mosfet_models"
section: "08_hisim_hv2"
section_number: "11.7"
topic: "08_hisim_hv2"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/spicelib/devices/hisimhv1/hisimhv.h"
related_chapters:
  - "07_hisim2.md"
domain_concepts:
  - "device_model_contract"
canonical_chain_tags:
  - "device_load_dispatch_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 6
last_updated_from_source_at: "2026-04-09T03:39:07.072860+00:00"
---

# HiSIM-HV {#hisim-hv2}

## Overview {#overview}

High-voltage HiSIM derivatives share the `hisimhv1/` tree; the public header `hisimhv.h` documents the exported interface used by companion `.c` sources in the same directory. Trace `*load.c` within `src/spicelib/devices/hisimhv1/` for the stamping equations—naming follows the HiSIM-HV code generator conventions.

## Source Files {#source-files}

- **`src/spicelib/devices/hisimhv1/hisimhv.h`**
- **`src/spicelib/devices/hisimhv1/*.c`** — implementation companions.

## Related Chapters {#related-chapters}

- [HiSIM2](07_hisim2.md)
