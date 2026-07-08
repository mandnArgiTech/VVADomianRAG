---
title: "EKV (ADMS)"
chapter: "11_mosfet_models"
section: "06_ekv"
section_number: "11.5"
topic: "06_ekv"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/spicelib/devices/dev.c"
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
estimated_reading_minutes: 6
last_updated_from_source_at: "2026-04-09T03:39:07.104114+00:00"
---

# EKV (ADMS) {#ekv}

## Overview {#overview}

The EKV model is compiled from Verilog-A via ADMS and registered alongside other ADMS devices in `dev.c` (`get_ekv_info`, [Source: src/spicelib/devices/dev.c#L204-L205]). Trace the generated interface headers under `src/spicelib/devices/adms/ekv/` in a full build tree.

## BSIM6 note {#bsim6}

This repository omits BSIM6 (`devices/bsim6/` absent); see chapter README and [`INDEX.md`](../INDEX.md).

<!-- source: src/spicelib/devices/dev.c -->

## Source Files {#source-files}

- **`src/spicelib/devices/dev.c`**

## Related Chapters {#related-chapters}

- [BSIM4](04_bsim4.md)
