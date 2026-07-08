---
title: "BJT VBIC"
chapter: "10_diode_and_bjt_models"
section: "03_bjt_vbic"
section_number: "10.3"
topic: "03_bjt_vbic"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/spicelib/devices/vbic/vbicload.c"
related_chapters:
  - "02_bjt_gummel_poon.md"
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

# BJT VBIC {#bjt-vbic}

## Overview {#overview}

The VBIC model’s `*load.c` file applies `DEVpnjlim` to each intrinsic junction voltage before evaluating transport currents—mirroring the limiting strategy used in simpler diodes but extended to the VBIC node set ([Source: src/spicelib/devices/vbic/vbicload.c#L743-L753] region).

<!-- source: src/spicelib/devices/vbic/vbicload.c -->

## Source Files {#source-files}

- **`src/spicelib/devices/vbic/vbicload.c`**

## Related Chapters {#related-chapters}

- [Gummel-Poon BJT](02_bjt_gummel_poon.md)
