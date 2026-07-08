---
title: "HiSIM2"
chapter: "11_mosfet_models"
section: "07_hisim2"
section_number: "11.6"
topic: "07_hisim2"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/spicelib/devices/hisim2/hsm2ld.c"
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

# HiSIM2 {#hisim2}

## Overview {#overview}

`HSM2load` evaluates the HiSIM2 surface-potential-based model; builds with `USE_OMP` parallelize instance evaluations via `HSM2LoadOMP` ([Source: src/spicelib/devices/hisim2/hsm2ld.c#L182-L199]).

<!-- source: src/spicelib/devices/hisim2/hsm2ld.c -->

## Source Files {#source-files}

- **`src/spicelib/devices/hisim2/hsm2ld.c`**

## Related Chapters {#related-chapters}

- [BSIM4](04_bsim4.md)
