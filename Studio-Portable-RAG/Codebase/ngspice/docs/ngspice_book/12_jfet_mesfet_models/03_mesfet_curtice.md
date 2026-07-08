---
title: "MESFET Curtice"
chapter: "12_jfet_mesfet_models"
section: "03_mesfet_curtice"
section_number: "12.3"
topic: "03_mesfet_curtice"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/spicelib/devices/mes/mesload.c"
  - "src/spicelib/devices/mes/mesinit.c"
related_chapters:
  - "04_mesfet_statz.md"
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

# MESFET Curtice {#mesfet-curtice}

## Overview {#overview}

The Curtice MESFET is handled by `MESload`, registered from `mesinit.c` ([Source: src/spicelib/devices/mes/mesinit.c#L45], [Source: src/spicelib/devices/mes/mesload.c#L22]).

<!-- source: src/spicelib/devices/mes/mesload.c -->

## Source Files {#source-files}

- **`src/spicelib/devices/mes/mesload.c`**
- **`src/spicelib/devices/mes/mesinit.c`**

## Related Chapters {#related-chapters}

- [Statz model](04_mesfet_statz.md)
