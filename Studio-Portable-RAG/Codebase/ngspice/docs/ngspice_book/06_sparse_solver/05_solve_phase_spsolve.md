---
title: "Solve phase (SMPsolve / spSolve)"
chapter: "06_sparse_solver"
section: "05_solve_phase_spsolve"
section_number: "6.5"
topic: "05_solve_phase_spsolve"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/maths/sparse/spsmp.c"
  - "src/maths/sparse/spsolve.c"
related_chapters:
  - "02_sparse_lu_factorization.md"
domain_concepts:
  - "sparse_lu_factorization"
canonical_chain_tags:
  - "sparse_solve_chain"
numerical_invariants_introduced:
  - "sparse_lu_factorization"
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 8
last_updated_from_source_at: "2026-04-09T03:39:07.072860+00:00"
---

# Solve phase (`SMPsolve`) {#solve-phase-spsolve}

## Overview {#overview}

`SMPsolve` wraps `spSolve`, allowing RHS and solution vectors to alias ([Source: src/maths/sparse/spsmp.c#L229-L237]).

`spSolve` performs sparse forward elimination and back substitution, exploiting RHS sparsity and storing intermediates allocated during factorization ([Source: src/maths/sparse/spsolve.c#L72-L108, L126-L128]).

<!-- source: src/maths/sparse/spsmp.c -->
<!-- source: src/maths/sparse/spsolve.c -->

## Source Files {#source-files}

- **`src/maths/sparse/spsmp.c`**
- **`src/maths/sparse/spsolve.c`**

## Canonical Chains {#canonical-chains}

- `sparse_solve_chain`
