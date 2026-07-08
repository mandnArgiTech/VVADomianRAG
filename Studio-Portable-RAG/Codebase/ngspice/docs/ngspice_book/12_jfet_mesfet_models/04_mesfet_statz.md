---
title: "MESFET Statz"
chapter: "12_jfet_mesfet_models"
section: "04_mesfet_statz"
section_number: "12.4"
topic: "04_mesfet_statz"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/spicelib/devices/mesa/mesaload.c"
related_chapters:
  - "03_mesfet_curtice.md"
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

# MESFET Statz {#mesfet-statz}

## Overview {#overview}

The Statz et al. model is implemented as `MESAload` in `mesa/mesaload.c` ([Source: src/spicelib/devices/mesa/mesaload.c#L37]).

<!-- source: src/spicelib/devices/mesa/mesaload.c -->

## Source Files {#source-files}

- **`src/spicelib/devices/mesa/mesaload.c`**

## Related Chapters {#related-chapters}

- [Curtice MESFET](03_mesfet_curtice.md)
