---
title: "BJT HiCUM2"
chapter: "10_diode_and_bjt_models"
section: "04_bjt_hicum2"
section_number: "10.4"
topic: "04_bjt_hicum2"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/spicelib/devices/dev.c"
  - "src/spicelib/devices/adms/hicum2/admsva/hicum2.va"
related_chapters:
  - "03_bjt_vbic.md"
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

# BJT HiCUM2 {#bjt-hicum2}

## Overview {#overview}

HiCUM2 is integrated through the **ADMS** flow: the Verilog-A source `src/spicelib/devices/adms/hicum2/admsva/hicum2.va` is compiled into C that exposes a standard `SPICEdev` table, registered via `get_hicum2_info` in the optional `static_devices[]` list ([Source: src/spicelib/devices/dev.c#L123, L202]).

When ADMS is disabled in a build, the device is absent—consult your `config.h` / build logs.

<!-- source: src/spicelib/devices/dev.c -->

## Source Files {#source-files}

- **`src/spicelib/devices/dev.c`** — registration hook.
- **`src/spicelib/devices/adms/hicum2/admsva/hicum2.va`** — authoritative model equations prior to ADMS translation.

## Related Chapters {#related-chapters}

- [VBIC](03_bjt_vbic.md)
