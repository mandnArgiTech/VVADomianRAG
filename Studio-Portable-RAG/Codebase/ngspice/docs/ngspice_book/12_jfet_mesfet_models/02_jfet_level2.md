---
title: "JFET level 2"
chapter: "12_jfet_mesfet_models"
section: "02_jfet_level2"
section_number: "12.2"
topic: "02_jfet_level2"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/spicelib/devices/jfet2/jfet2load.c"
  - "src/spicelib/devices/jfet2/jfet2init.c"
related_chapters:
  - "01_jfet_level1.md"
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

# JFET level 2 {#jfet-level2}

## Overview {#overview}

`JFET2load` is registered in `JFET2info` ([Source: src/spicelib/devices/jfet2/jfet2init.c#L45]) and implemented in `jfet2load.c` ([Source: src/spicelib/devices/jfet2/jfet2load.c#L22]).

<!-- source: src/spicelib/devices/jfet2/jfet2init.c -->
<!-- source: src/spicelib/devices/jfet2/jfet2load.c -->

## Source Files {#source-files}

- **`src/spicelib/devices/jfet2/jfet2load.c`**
- **`src/spicelib/devices/jfet2/jfet2init.c`**

## Related Chapters {#related-chapters}

- [JFET level 1](01_jfet_level1.md)
