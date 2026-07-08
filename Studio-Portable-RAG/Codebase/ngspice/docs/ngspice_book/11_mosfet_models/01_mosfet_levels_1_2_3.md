---
title: "MOSFET levels 1–3"
chapter: "11_mosfet_models"
section: "01_mosfet_levels_1_2_3"
section_number: "11.1"
topic: "01_mosfet_levels_1_2_3"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/spicelib/devices/mos1/mos1load.c"
related_chapters:
  - "../07_device_model_contract/03_devload_load_function.md"
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

# MOSFET levels 1–3 {#mosfet-levels-1-2-3}

## Overview {#overview}

Level-1 MOS is implemented by `MOS1load`, which computes Shichman-Hodges currents, charges, and capacitances before stamping the Jacobian ([Source: src/spicelib/devices/mos1/mos1load.c#L16-L20]). Levels 2 and 3 follow the same structural pattern in `mos2/` and `mos3/` directories with their respective `*load.c` files.

<!-- source: src/spicelib/devices/mos1/mos1load.c -->

## Source Files {#source-files}

- **`src/spicelib/devices/mos1/mos1load.c`**
- **`src/spicelib/devices/mos2/`**, **`src/spicelib/devices/mos3/`** — parallel implementations.
