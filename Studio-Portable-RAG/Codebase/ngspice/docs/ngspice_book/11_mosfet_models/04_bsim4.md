---
title: "BSIM4"
chapter: "11_mosfet_models"
section: "04_bsim4"
section_number: "11.4"
topic: "04_bsim4"
mission_primary: "kernel_reimplementation"
mission_secondary: ["circuit_design_validation"]
related_files:
  - "src/spicelib/devices/bsim4/b4ld.c"
  - "src/spicelib/devices/bsim4/bsim4init.c"
related_chapters:
  - "../07_device_model_contract/01_spicedev_struct_anatomy.md"
domain_concepts:
  - "device_model_contract"
canonical_chain_tags:
  - "device_model_mosfet_bsim4"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 9
last_updated_from_source_at: "2026-04-09T03:39:07.072860+00:00"
---

# BSIM4 {#bsim4}

## Overview {#overview}

BSIM4 is the flagship MOS model: `BSIM4info` wires `BSIM4load`, `BSIM4acLoad`, `BSIM4trunc`, `BSIM4convTest`, `BSIM4noise`, and SOA checks ([Source: src/spicelib/devices/bsim4/bsim4init.c#L43-L70]). The numerical kernel lives in `b4ld.c` (`BSIM4load`, [Source: src/spicelib/devices/bsim4/b4ld.c#L72]).

<!-- source: src/spicelib/devices/bsim4/bsim4init.c -->
<!-- source: src/spicelib/devices/bsim4/b4ld.c -->

## Source Files {#source-files}

- **`src/spicelib/devices/bsim4/b4ld.c`**
- **`src/spicelib/devices/bsim4/bsim4init.c`**

## Related Chapters {#related-chapters}

- [SPICEdev anatomy](../07_device_model_contract/01_spicedev_struct_anatomy.md)
