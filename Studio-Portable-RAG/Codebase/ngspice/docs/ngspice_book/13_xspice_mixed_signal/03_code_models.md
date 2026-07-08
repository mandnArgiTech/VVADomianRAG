---
title: "Code models"
chapter: "13_xspice_mixed_signal"
section: "03_code_models"
section_number: "13.3"
topic: "03_code_models"
mission_primary: "kernel_reimplementation"
mission_secondary: ["circuit_design_validation"]
related_files:
  - "src/include/ngspice/mif.h"
related_chapters:
  - "04_analog_digital_interfacing.md"
domain_concepts:
  - "xspice_mixed_signal"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 7
last_updated_from_source_at: "2026-04-09T03:39:07.065678+00:00"
---

# Code models {#code-models}

## Overview {#overview}

Model-Interface code models read global simulation metadata from `Mif_Circuit_Info_t`—initialization flags, analysis type, analog vs event call path, and the current event time (`evt_step`, [Source: src/include/ngspice/mif.h#L49-L55]). This is how C-coded behavioral blocks stay synchronized with `CKTmode` and `CKTtime`.

<!-- source: src/include/ngspice/mif.h -->

## Source Files {#source-files}

- **`src/include/ngspice/mif.h`**
- **`src/xspice/mif/`** — implementation sources (browse for `MIFload`).

## Related Chapters {#related-chapters}

- [Analog/digital interfacing](04_analog_digital_interfacing.md)
