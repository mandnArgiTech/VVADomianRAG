---
title: "Sparse solve chain"
chapter: "23_canonical_chains_reference"
section: "06_sparse_solve_chain"
section_number: "23.6"
topic: "sparse_solve_chain"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/maths/sparse/spbuild.c"
  - "src/maths/sparse/spfactor.c"
  - "src/maths/sparse/spsolve.c"
related_chapters:
  - "../06_sparse_solver/02_sparse_lu_factorization.md"
  - "../06_sparse_solver/05_solve_phase_spsolve.md"
domain_concepts:
  - "sparse_lu_factorization"
canonical_chain_tags:
  - "sparse_solve_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 7
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Sparse solve chain {#sparse-solve-chain}

## Summary {#summary}

Structural build (`spbuild` / element insertion) → numeric factor via `spFactor` ([Source: src/maths/sparse/spfactor.c#L367]) → `spSolve` for forward/back substitution ([Source: src/maths/sparse/spsolve.c#L127-L130]).

## Stages {#stages}

`build_or_clear` → `factor` → `solve` (`rag_index.json`).

## Deep dives {#deep-dives}

- [LU factorization](../06_sparse_solver/02_sparse_lu_factorization.md)
- [Solve phase](../06_sparse_solver/05_solve_phase_spsolve.md)
