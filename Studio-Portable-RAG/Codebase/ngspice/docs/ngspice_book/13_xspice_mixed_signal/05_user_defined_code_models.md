---
title: "User-defined code models"
chapter: "13_xspice_mixed_signal"
section: "05_user_defined_code_models"
section_number: "13.5"
topic: "05_user_defined_code_models"
mission_primary: "circuit_design_validation"
mission_secondary: ["kernel_reimplementation"]
related_files:
  - "src/include/ngspice/mif.h"
related_chapters:
  - "03_code_models.md"
domain_concepts:
  - "xspice_mixed_signal"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 6
last_updated_from_source_at: "2026-04-09T03:39:07.065678+00:00"
---

# User-defined code models {#user-defined-code-models}

## Overview {#overview}

User extensions compile into shared libraries that register with the MIF infrastructure. The global `Mif_Info_t` block passes circuit pointers, instance pointers, and breakpoint state into each code model invocation ([Source: src/include/ngspice/mif.h#L70-L77]).

Detailed authoring steps live outside this kernel-focused book; start from the XSPICE documentation shipped with ngspice and the `cm_` examples under `src/xspice/`.

## Source Files {#source-files}

- **`src/include/ngspice/mif.h`**

## Related Chapters {#related-chapters}

- [Code models](03_code_models.md)
