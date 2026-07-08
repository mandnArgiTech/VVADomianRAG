---
title: "GMIN stepping mechanics"
chapter: "04_convergence_aids"
section: "02_gmin_stepping_mechanics"
section_number: "4.2"
topic: "02_gmin_stepping_mechanics"
mission_primary: "kernel_reimplementation"
mission_secondary: ["circuit_design_validation"]
related_files:
  - "src/spicelib/analysis/cktop.c"
related_chapters:
  - "01_convergence_aid_ladder.md"
  - "../18_options_and_tolerances/01_options_overview.md"
domain_concepts:
  - "gmin_stepping"
canonical_chain_tags:
  - "convergence_aid_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 9
last_updated_from_source_at: "2026-04-09T03:39:07.072860+00:00"
---

# GMIN stepping mechanics {#gmin-stepping-mechanics}

## Overview {#overview}

When `CKTnumGminSteps == 1`, `CKTop` calls `dynamic_gmin`, otherwise `spice3_gmin` ([Source: src/spicelib/analysis/cktop.c#L52-L56]). Both routines live in `cktop.c` immediately after `CKTop` and implement progressive shunt conductance ramps to ease Newton into a basin of attraction ([Source: src/spicelib/analysis/cktop.c#L117-L158] for `dynamic_gmin` header commentary).

The `.options gminsteps` value maps to `CKTnumGminSteps` via `OPT_GMINSTEPS` ([Source: src/spicelib/analysis/cktsopt.c#L91-L93, L249]).

<!-- source: src/spicelib/analysis/cktop.c -->
<!-- source: src/spicelib/analysis/cktsopt.c -->

## Source Files {#source-files}

- **`src/spicelib/analysis/cktop.c`**
- **`src/spicelib/analysis/cktsopt.c`**

## Related Chapters {#related-chapters}

- [Convergence ladder](01_convergence_aid_ladder.md)
