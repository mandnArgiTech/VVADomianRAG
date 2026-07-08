---
title: "DEVtemperature"
chapter: "07_device_model_contract"
section: "08_devtemperature_temp_resolution"
section_number: "7.8"
topic: "08_devtemperature_temp_resolution"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/include/ngspice/devdefs.h"
  - "src/spicelib/devices/bsim4/bsim4init.c"
related_chapters:
  - "../18_options_and_tolerances/README.md"
domain_concepts:
  - "device_model_contract"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 6
last_updated_from_source_at: "2026-04-09T03:39:07.065678+00:00"
---

# DEVtemperature {#devtemperature-temp-resolution}

## Overview {#overview}

`DEVtemperature` recomputes temperature-dependent parameters (bandgap references, mobility scalings, leakage factors) before nonlinear solves. Signature: `int (*DEVtemperature)(GENmodel*, CKTcircuit*)` ([Source: src/include/ngspice/devdefs.h#L61-L62]). BSIM4 binds `BSIM4temp` ([Source: src/spicelib/devices/bsim4/bsim4init.c#L49]).

<!-- source: src/include/ngspice/devdefs.h -->
<!-- source: src/spicelib/devices/bsim4/bsim4init.c -->

## What This Section Does {#what-it-does}

Signals that `CKTtemp` / `CKTnomTemp` fields on `CKTcircuit` ([Source: src/include/ngspice/cktdefs.h#L93-L95]) feed into each model’s preprocessing path before `DEVload` runs at the operating temperature.

## Source Files {#source-files}

- **`src/include/ngspice/devdefs.h`**
- **`src/spicelib/devices/bsim4/bsim4init.c`**

## Related Chapters {#related-chapters}

- [Options & tolerances](../18_options_and_tolerances/README.md) — `.temp`, `.option temp`.
