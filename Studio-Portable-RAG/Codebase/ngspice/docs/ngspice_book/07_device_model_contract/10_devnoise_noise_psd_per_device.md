---
title: "DEVnoise"
chapter: "07_device_model_contract"
section: "10_devnoise_noise_psd_per_device"
section_number: "7.10"
topic: "10_devnoise_noise_psd_per_device"
mission_primary: "kernel_reimplementation"
mission_secondary: ["circuit_design_validation"]
related_files:
  - "src/include/ngspice/devdefs.h"
  - "src/spicelib/devices/bsim4/bsim4init.c"
related_chapters:
  - "../03_analysis_drivers/05_noise_analysis_noisean.md"
domain_concepts:
  - "noise_analysis"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 6
last_updated_from_source_at: "2026-04-09T03:39:07.065678+00:00"
---

# DEVnoise (noise PSD per device) {#devnoise-noise-psd-per-device}

## Overview {#overview}

`DEVnoise` contributes shot, thermal, and flicker noise densities during `.noise` analysis. The pointer is `int (*DEVnoise)(int, int, GENmodel*, CKTcircuit*, Ndata *, double *)` ([Source: src/include/ngspice/devdefs.h#L103-L104]). BSIM4 registers `BSIM4noise` ([Source: src/spicelib/devices/bsim4/bsim4init.c#L69]).

<!-- source: src/include/ngspice/devdefs.h -->
<!-- source: src/spicelib/devices/bsim4/bsim4init.c -->

## Source Files {#source-files}

- **`src/include/ngspice/devdefs.h`**
- **`src/spicelib/devices/bsim4/bsim4init.c`**

## Related Chapters {#related-chapters}

- [Noise analysis driver](../03_analysis_drivers/05_noise_analysis_noisean.md)
