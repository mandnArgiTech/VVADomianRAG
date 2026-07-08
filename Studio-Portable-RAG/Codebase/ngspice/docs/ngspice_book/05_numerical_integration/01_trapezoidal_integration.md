---
title: "Trapezoidal integration"
chapter: "05_numerical_integration"
section: "01_trapezoidal_integration"
section_number: "5.1"
topic: "01_trapezoidal_integration"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/maths/ni/niinteg.c"
  - "src/spicelib/analysis/cktsopt.c"
related_chapters:
  - "../00_foundations/05_numerical_integration_for_transient.md"
domain_concepts:
  - "numerical_integration"
canonical_chain_tags:
  - "transient_step_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 8
last_updated_from_source_at: "2026-04-09T03:39:07.069653+00:00"
---

# Trapezoidal integration {#trapezoidal-integration}

## Overview {#overview}

When `ckt->CKTintegrateMethod == TRAPEZOIDAL`, `NIintegrate` uses order 1 or 2 combinations of `CKTag[]` coefficients with historic charge states `CKTstate0[qcap]` / `CKTstate1[qcap]` ([Source: src/maths/ni/niinteg.c#L23-L40]).

`.options method=trap` selects trapezoidal integration via `OPT_METHOD` ([Source: src/spicelib/analysis/cktsopt.c#L133-L138, L264]).

<!-- source: src/maths/ni/niinteg.c -->
<!-- source: src/spicelib/analysis/cktsopt.c -->

## Source Files {#source-files}

- **`src/maths/ni/niinteg.c`**
- **`src/spicelib/analysis/cktsopt.c`**

## Related Chapters {#related-chapters}

- [Integration primer](../00_foundations/05_numerical_integration_for_transient.md)

## Canonical Chains {#canonical-chains}

- `transient_step_chain`
