---
title: "BJT Gummel-Poon"
chapter: "10_diode_and_bjt_models"
section: "02_bjt_gummel_poon"
section_number: "10.2"
topic: "02_bjt_gummel_poon"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/spicelib/devices/bjt/bjtload.c"
related_chapters:
  - "01_diode_model.md"
domain_concepts:
  - "device_model_contract"
canonical_chain_tags:
  - "device_load_dispatch_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 8
last_updated_from_source_at: "2026-04-09T03:39:07.072860+00:00"
---

# BJT Gummel-Poon {#bjt-gummel-poon}

## Overview {#overview}

`BJTload` is the per-iteration entry point for the classic Gummel-Poon bipolar model, assembling charges, capacitances, and conductive stamps into the MNA matrix each Newton step ([Source: src/spicelib/devices/bjt/bjtload.c#L7-L25]).

<!-- source: src/spicelib/devices/bjt/bjtload.c -->

## Source Files {#source-files}

- **`src/spicelib/devices/bjt/bjtload.c`**

## Related Chapters {#related-chapters}

- [Diode model](01_diode_model.md)
