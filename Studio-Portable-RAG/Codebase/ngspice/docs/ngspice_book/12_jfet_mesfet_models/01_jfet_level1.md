---
title: "JFET level 1"
chapter: "12_jfet_mesfet_models"
section: "01_jfet_level1"
section_number: "12.1"
topic: "01_jfet_level1"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/spicelib/devices/jfet/jfetload.c"
related_chapters:
  - "02_jfet_level2.md"
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

# JFET level 1 {#jfet-level1}

## Overview {#overview}

`JFETload` implements the classic Shurman-JFET equations, updating drain current, charges, and conductances before stamping the MNA entries ([Source: src/spicelib/devices/jfet/jfetload.c#L19-L24]).

<!-- source: src/spicelib/devices/jfet/jfetload.c -->

## Source Files {#source-files}

- **`src/spicelib/devices/jfet/jfetload.c`**

## Related Chapters {#related-chapters}

- [JFET level 2](02_jfet_level2.md)
