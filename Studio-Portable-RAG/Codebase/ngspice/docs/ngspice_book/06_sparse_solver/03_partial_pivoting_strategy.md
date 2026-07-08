---
title: "Partial pivoting strategy"
chapter: "06_sparse_solver"
section: "03_partial_pivoting_strategy"
section_number: "6.3"
topic: "03_partial_pivoting_strategy"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/maths/sparse/spfactor.c"
  - "src/maths/ni/niiter.c"
related_chapters:
  - "../02_numerical_kernel_core/07_matrix_singularity_handling.md"
domain_concepts:
  - "sparse_partial_pivoting"
canonical_chain_tags:
  - "sparse_solve_chain"
numerical_invariants_introduced:
  - "sparse_partial_pivoting"
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 8
last_updated_from_source_at: "2026-04-20T02:48:52Z"
---

# Partial pivoting strategy {#partial-pivoting-strategy}

## Overview {#overview}

`spOrderAndFactor` accepts `RelThreshold` and `AbsThreshold` arguments, defaulting to matrix-stored values when callers pass non-positive numbers ([Source: src/maths/sparse/spfactor.c#L245-L252]). These map directly to `CKTpivotRelTol` / `CKTpivotAbsTol` in `NIiter` when it calls `SMPreorder` ([Source: src/maths/ni/niiter.c#L122-L123]).

The routine searches for stable pivots column-wise (`FindLargestInCol` path, [Source: src/maths/sparse/spfactor.c#L257-L259]).

<!-- source: src/maths/sparse/spfactor.c -->
<!-- source: src/maths/ni/niiter.c -->

## Source Files {#source-files}

- **`src/maths/sparse/spfactor.c`**
- **`src/maths/ni/niiter.c`**

## Canonical Chains {#canonical-chains}

- `sparse_solve_chain`
