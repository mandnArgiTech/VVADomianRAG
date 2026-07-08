---
title: "Source stepping mechanics"
chapter: "04_convergence_aids"
section: "03_source_stepping_mechanics"
section_number: "4.3"
topic: "03_source_stepping_mechanics"
mission_primary: "kernel_reimplementation"
mission_secondary: ["circuit_design_validation"]
related_files:
  - "src/spicelib/analysis/cktop.c"
related_chapters:
  - "01_convergence_aid_ladder.md"
domain_concepts:
  - "source_stepping"
canonical_chain_tags:
  - "convergence_aid_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 8
last_updated_from_source_at: "2026-04-09T03:39:07.072860+00:00"
---

# Source stepping mechanics {#source-stepping-mechanics}

## Overview {#overview}

After GMIN stepping fails or is skipped, `CKTop` scales independent sources via `gillespie_src` when `CKTnumSrcSteps == 1`, otherwise `spice3_src` ([Source: src/spicelib/analysis/cktop.c#L67-L71]). The comment block in `CKTop` explains the intent: converge at zero excitation, then ramp sources toward their final values ([Source: src/spicelib/analysis/cktop.c#L61-L65]).

`OPT_SRCSTEPS` / `itl6` aliases populate `CKTnumSrcSteps` ([Source: src/spicelib/analysis/cktsopt.c#L88-L90, L247-L248]).

<!-- source: src/spicelib/analysis/cktop.c -->
<!-- source: src/spicelib/analysis/cktsopt.c -->

## Source Files {#source-files}

- **`src/spicelib/analysis/cktop.c`**
- **`src/spicelib/analysis/cktsopt.c`**

## Related Chapters {#related-chapters}

- [Convergence ladder](01_convergence_aid_ladder.md)
