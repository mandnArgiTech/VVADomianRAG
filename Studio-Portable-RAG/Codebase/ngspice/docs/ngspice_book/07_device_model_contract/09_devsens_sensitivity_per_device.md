---
title: "DEVsens (sensitivity hooks)"
chapter: "07_device_model_contract"
section: "09_devsens_sensitivity_per_device"
section_number: "7.9"
topic: "09_devsens_sensitivity_per_device"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/include/ngspice/devdefs.h"
related_chapters:
  - "../03_analysis_drivers/08_sensitivity_adjoint_senan.md"
domain_concepts:
  - "sensitivity_analysis"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 6
last_updated_from_source_at: "2026-04-09T03:39:07.065678+00:00"
---

# DEVsens (sensitivity hooks) {#devsens-sensitivity-per-device}

## Overview {#overview}

`SPICEdev` reserves multiple callbacks for sensitivity analysis (`DEVsenSetup`, `DEVsenLoad`, `DEVsenUpdate`, `DEVsenAcLoad`, `DEVsenPrint`, `DEVsenTrunc`) ([Source: src/include/ngspice/devdefs.h#L89-L100]). A device participates in `.sens` workflows by wiring these to non-NULL implementations; BSIM4 leaves them `NULL` in the stock table shown earlier, meaning sensitivity support depends on device-specific development ([Source: src/spicelib/devices/bsim4/bsim4init.c#L62-L67]).

<!-- source: src/include/ngspice/devdefs.h -->
<!-- source: src/spicelib/devices/bsim4/bsim4init.c -->

## Source Files {#source-files}

- **`src/include/ngspice/devdefs.h`**

## Related Chapters {#related-chapters}

- [Sensitivity analysis](../03_analysis_drivers/08_sensitivity_adjoint_senan.md)
