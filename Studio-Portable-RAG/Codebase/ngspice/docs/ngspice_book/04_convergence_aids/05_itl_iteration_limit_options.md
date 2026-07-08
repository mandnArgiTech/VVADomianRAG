---
title: "ITL iteration limit options"
chapter: "04_convergence_aids"
section: "05_itl_iteration_limit_options"
section_number: "4.5"
topic: "05_itl_iteration_limit_options"
mission_primary: "kernel_reimplementation"
mission_secondary: ["circuit_design_validation"]
related_files:
  - "src/spicelib/analysis/cktsopt.c"
  - "src/spicelib/devices/cktinit.c"
  - "src/spicelib/analysis/cktdojob.c"
related_chapters:
  - "../18_options_and_tolerances/04_itl_and_limit_options.md"
domain_concepts:
  - "iteration_limits"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 8
last_updated_from_source_at: "2026-04-09T03:39:07.072860+00:00"
---

# ITL iteration limit options {#itl-iteration-limit-options}

## Overview {#overview}

Iteration budgets are stored on `CKTcircuit` as `CKTdcMaxIter`, `CKTdcTrcvMaxIter`, and `CKTtranMaxIter`, defaulting to `100`, `50`, and `10` in `CKTinit` ([Source: src/spicelib/devices/cktinit.c#L60-L62]).

`.options` processing maps:

| Option | Field | Source |
|--------|-------|--------|
| `itl1` | `TSKdcMaxIter` | [Source: src/spicelib/analysis/cktsopt.c#L75-L77, L242] |
| `itl2` | `TSKdcTrcvMaxIter` | [Source: src/spicelib/analysis/cktsopt.c#L78-L80, L243] |
| `itl4` | `TSKtranMaxIter` | [Source: src/spicelib/analysis/cktsopt.c#L83-L85, L245] |

`cktdojob.c` copies task limits into the live circuit (`CKTdcMaxIter = task->TSKdcMaxIter`, [Source: src/spicelib/analysis/cktdojob.c#L56]).

<!-- source: src/spicelib/analysis/cktsopt.c -->
<!-- source: src/spicelib/devices/cktinit.c -->
<!-- source: src/spicelib/analysis/cktdojob.c -->

## Source Files {#source-files}

- **`src/spicelib/analysis/cktsopt.c`**
- **`src/spicelib/devices/cktinit.c`**
- **`src/spicelib/analysis/cktdojob.c`**

## Related Chapters {#related-chapters}

- [ITL deep dive](../18_options_and_tolerances/03_iteration_limit_options_itl.md)
