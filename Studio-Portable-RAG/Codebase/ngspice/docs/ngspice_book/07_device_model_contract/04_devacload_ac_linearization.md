---
title: "DEVacLoad"
chapter: "07_device_model_contract"
section: "04_devacload_ac_linearization"
section_number: "7.4"
topic: "04_devacload_ac_linearization"
mission_primary: "kernel_reimplementation"
mission_secondary: ["circuit_design_validation"]
related_files:
  - "src/include/ngspice/devdefs.h"
  - "src/spicelib/devices/bsim4/bsim4init.c"
related_chapters:
  - "../03_analysis_drivers/04_ac_small_signal_acan.md"
domain_concepts:
  - "ac_small_signal_analysis"
canonical_chain_tags:
  - "ac_analysis_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 7
last_updated_from_source_at: "2026-04-09T03:39:07.065678+00:00"
---

# DEVacLoad (AC linearization) {#devacload-ac-linearization}

## Overview {#overview}

`DEVacLoad` stamps complex-valued small-signal contributions after a DC operating point (or other linearization point) is known. The function pointer lives in `SPICEdev` ([Source: src/include/ngspice/devdefs.h#L68-L69]). BSIM4 binds `BSIM4acLoad` ([Source: src/spicelib/devices/bsim4/bsim4init.c#L52]).

<!-- source: src/include/ngspice/devdefs.h -->
<!-- source: src/spicelib/devices/bsim4/bsim4init.c -->

## What This Section Does {#what-it-does}

Distinguishes AC analysis from resistive `DEVload`: capacitors/inductors and small-signal conductances appear here using `CKTirhs*` vectors defined on `CKTcircuit` ([Source: src/include/ngspice/cktdefs.h#L115-L118]).

## Source Files {#source-files}

- **`src/include/ngspice/devdefs.h`**
- **`src/spicelib/devices/bsim4/bsim4init.c`**

## Related Chapters {#related-chapters}

- [AC analysis driver](../03_analysis_drivers/04_ac_small_signal_acan.md)

## Canonical Chains {#canonical-chains}

- `ac_analysis_chain` (`rag_index.json`)
