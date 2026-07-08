---
title: "MOSFET levels 6–9"
chapter: "11_mosfet_models"
section: "02_mosfet_level_6_9"
section_number: "11.2"
topic: "02_mosfet_level_6_9"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/spicelib/devices/mos6/mos6load.c"
  - "src/spicelib/devices/mos9/mos9load.c"
related_chapters:
  - "01_mosfet_levels_1_2_3.md"
domain_concepts:
  - "device_model_contract"
canonical_chain_tags:
  - "device_load_dispatch_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 7
last_updated_from_source_at: "2026-04-09T03:39:07.072860+00:00"
---

# MOSFET levels 6–9 {#mosfet-level-6-9}

## Overview {#overview}

Intermediate Berkeley compact models live in `mos6/` and `mos9/`. Each provides `MOS6load` / `MOS9load` with the same high-level contract as `MOS1load`: evaluate terminal currents, apply `DEVfetlim` / `DEVpnjlim` to internal voltages, then stamp conductances and capacitive companions.

Example limiting usage appears throughout `mos9load.c` ([Source: src/spicelib/devices/mos9/mos9load.c#L352-L371] — see repository for full context).

## Source Files {#source-files}

- **`src/spicelib/devices/mos6/mos6load.c`**
- **`src/spicelib/devices/mos9/mos9load.c`**

## Related Chapters {#related-chapters}

- [Levels 1–3](01_mosfet_levels_1_2_3.md)
