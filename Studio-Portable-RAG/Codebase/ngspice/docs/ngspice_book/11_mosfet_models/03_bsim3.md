---
title: "BSIM3"
chapter: "11_mosfet_models"
section: "03_bsim3"
section_number: "11.3"
topic: "03_bsim3"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/spicelib/devices/bsim3/b3ld.c"
  - "src/spicelib/devices/bsim3/bsim3init.c"
related_chapters:
  - "04_bsim4.md"
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

# BSIM3 {#bsim3}

## Overview {#overview}

BSIM3 registers `BSIM3load` inside `BSIM3info` ([Source: src/spicelib/devices/bsim3/bsim3init.c#L44]). The implementation file `b3ld.c` defines the function beginning at the symbol `BSIM3load` ([Source: src/spicelib/devices/bsim3/b3ld.c#L42]).

<!-- source: src/spicelib/devices/bsim3/bsim3init.c -->
<!-- source: src/spicelib/devices/bsim3/b3ld.c -->

## Source Files {#source-files}

- **`src/spicelib/devices/bsim3/b3ld.c`**
- **`src/spicelib/devices/bsim3/bsim3init.c`**

## Related Chapters {#related-chapters}

- [BSIM4](04_bsim4.md)
