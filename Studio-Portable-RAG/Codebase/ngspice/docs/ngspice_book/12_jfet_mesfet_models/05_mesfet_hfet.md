---
title: "MESFET / HFET"
chapter: "12_jfet_mesfet_models"
section: "05_mesfet_hfet"
section_number: "12.5"
topic: "05_mesfet_hfet"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/spicelib/devices/hfet1/hfetload.c"
  - "src/spicelib/devices/hfet2/hfet2load.c"
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

# MESFET / HFET {#mesfet-hfet}

## Overview {#overview}

HFET models ship in two generations: `hfet1/hfetload.c` defines the original `HFETload`, while `hfet2/hfet2load.c` supplies the updated `HFET2load` path ([Source: src/spicelib/devices/hfet1/hfetload.c], [Source: src/spicelib/devices/hfet2/hfet2load.c]).

<!-- source: src/spicelib/devices/hfet1/hfetload.c -->
<!-- source: src/spicelib/devices/hfet2/hfet2load.c -->

## Source Files {#source-files}

- **`src/spicelib/devices/hfet1/hfetload.c`**
- **`src/spicelib/devices/hfet2/hfet2load.c`**

## Related Chapters {#related-chapters}

- [Curtice MESFET](03_mesfet_curtice.md)
