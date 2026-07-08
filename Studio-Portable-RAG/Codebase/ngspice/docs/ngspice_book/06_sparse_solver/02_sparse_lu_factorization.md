---
title: "Sparse LU factorization"
chapter: "06_sparse_solver"
section: "02_sparse_lu_factorization"
section_number: "6.2"
topic: "02_sparse_lu_factorization"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/maths/sparse/spsmp.c"
  - "src/maths/sparse/spfactor.c"
related_chapters:
  - "01_sparse_matrix_data_structure.md"
domain_concepts:
  - "sparse_lu_factorization"
canonical_chain_tags:
  - "sparse_solve_chain"
numerical_invariants_introduced:
  - "sparse_lu_factorization"
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 9
last_updated_from_source_at: "2026-04-09T03:39:07.072860+00:00"
---

# Sparse LU factorization {#sparse-lu-factorization}

## Overview {#overview}

Real factorization enters through `SMPluFac`, which sets the matrix real, applies `LoadGmin`, and calls `spFactor` ([Source: src/maths/sparse/spsmp.c#L168-L175]). Reordering + factorization for a fresh pivot sequence uses `SMPreorder` → `spOrderAndFactor` ([Source: src/maths/sparse/spsmp.c#L193-L199]).

`spOrderAndFactor` implements Markowitz-based pivot selection with relative/absolute thresholds and optional diagonal pivoting ([Source: src/maths/sparse/spfactor.c#L232-L259]).

<!-- source: src/maths/sparse/spsmp.c -->
<!-- source: src/maths/sparse/spfactor.c -->

## Source Files {#source-files}

- **`src/maths/sparse/spsmp.c`**
- **`src/maths/sparse/spfactor.c`**

## Canonical Chains {#canonical-chains}

- `sparse_solve_chain`
