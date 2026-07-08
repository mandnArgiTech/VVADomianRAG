---
title: "DEVtrunc (LTE per device)"
chapter: "07_device_model_contract"
section: "05_devtrunc_lte_per_device"
section_number: "7.5"
topic: "05_devtrunc_lte_per_device"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/include/ngspice/devdefs.h"
  - "src/spicelib/devices/bsim4/bsim4init.c"
related_chapters:
  - "../05_numerical_integration/05_lte_estimation_devtrunc.md"
  - "../03_analysis_drivers/03_transient_dctran.md"
domain_concepts:
  - "numerical_integration"
canonical_chain_tags:
  - "transient_step_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 7
last_updated_from_source_at: "2026-04-09T03:39:07.065678+00:00"
---

# DEVtrunc (LTE per device) {#devtrunc-lte-per-device}

## Overview {#overview}

`DEVtrunc` lets each device family contribute to the global local truncation error (LTE) estimate used to accept or reject a transient timestep. The callback signature is `int (*DEVtrunc)(GENmodel*, CKTcircuit*, double*)` ([Source: src/include/ngspice/devdefs.h#L64-L65]). BSIM4 exposes `BSIM4trunc` ([Source: src/spicelib/devices/bsim4/bsim4init.c#L50]).

<!-- source: src/include/ngspice/devdefs.h -->
<!-- source: src/spicelib/devices/bsim4/bsim4init.c -->

## What This Section Does {#what-it-does}

Identifies the per-device half of timestep control; analysis drivers aggregate these hints (see Chapter 5 and `DCtran`).

## Source Files {#source-files}

- **`src/include/ngspice/devdefs.h`**
- **`src/spicelib/devices/bsim4/bsim4init.c`**

## Related Chapters {#related-chapters}

- [LTE estimation](../05_numerical_integration/05_lte_estimation_devtrunc.md)
- [Transient driver](../03_analysis_drivers/03_transient_dctran.md)

## Canonical Chains {#canonical-chains}

- `transient_step_chain`
