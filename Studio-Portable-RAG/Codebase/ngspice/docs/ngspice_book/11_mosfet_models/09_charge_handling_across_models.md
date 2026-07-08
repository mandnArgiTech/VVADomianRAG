---
title: "Charge handling across models"
chapter: "11_mosfet_models"
section: "09_charge_handling_across_models"
section_number: "11.8"
topic: "09_charge_handling_across_models"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/spicelib/devices/mos1/mos1load.c"
  - "src/spicelib/devices/bsim4/b4ld.c"
related_chapters:
  - "../05_numerical_integration/04_charge_conserving_capacitor_stamps.md"
domain_concepts:
  - "charge_conservation"
canonical_chain_tags:
  - "transient_step_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 8
last_updated_from_source_at: "2026-04-09T03:39:07.072860+00:00"
---

# Charge handling across models {#charge-handling-across-models}

## Overview {#overview}

MOS models compute terminal charges (`ceqgs`, `ceqgd`, …) and map them into MNA history states each transient iteration—see the charge-equivalent assignments near the top of `MOS1load` ([Source: src/spicelib/devices/mos1/mos1load.c#L37-L42]).

Modern models (BSIM4, HiSIM, etc.) embed more elaborate partitioning between intrinsic and overlap charges, but the **interface** to the integrator remains: charges feed `NIintegrate` indirectly through stamp equations inside each `*load.c`.

## Source Files {#source-files}

- **`src/spicelib/devices/mos1/mos1load.c`** — pedagogical reference.
- **`src/spicelib/devices/bsim4/b4ld.c`** — production complexity.

## Related Chapters {#related-chapters}

- [Capacitor integration](../05_numerical_integration/04_charge_conserving_capacitor_stamps.md)
