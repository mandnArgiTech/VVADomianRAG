---
title: "Sparse matrices in circuit simulation"
chapter: "00_foundations"
section: "04_sparse_matrix_in_circuit_simulation"
section_number: "0.4"
topic: "04_sparse_matrix_in_circuit_simulation"
mission_primary: "kernel_reimplementation"
mission_secondary: ["circuit_design_validation"]
related_files:
  - "src/include/ngspice/cktdefs.h"
  - "src/maths/ni/niiter.c"
related_chapters:
  - "../06_sparse_solver/01_sparse_matrix_data_structure.md"
  - "../06_sparse_solver/02_sparse_lu_factorization.md"
  - "../02_numerical_kernel_core/02_newton_raphson_iteration_niiter.md"
domain_concepts:
  - "sparse_lu_factorization"
canonical_chain_tags:
  - "sparse_solve_chain"
numerical_invariants_introduced:
  - "sparse_lu_factorization"
glossary_terms_introduced:
  - "SMPmatrix"
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 10
last_updated_from_source_at: "2026-04-20T02:48:52Z"
---

# Sparse matrices in circuit simulation {#sparse-matrix-in-circuit-simulation}

## Overview {#overview}

Circuit matrices are sparse: each device touches only a handful of nodes, so storing a dense \(N \times N\) Jacobian would waste memory and time. ngspice represents the MNA Jacobian in `SMPmatrix *CKTmatrix` attached to `CKTcircuit` ([Source: src/include/ngspice/cktdefs.h#L109]). The Newton driver `NIiter` clears numeric entries each load, optionally reorders pivots, factors with `SMPluFac` or `SMPreorder`, and solves with `SMPsolve` ([Source: src/maths/ni/niiter.c#L52-L56, L103-L187]).

<!-- source: src/include/ngspice/cktdefs.h -->
<!-- source: src/maths/ni/niiter.c -->

## What This Section Does {#what-it-does}

Explains *why* Chapter 6 exists: every `CKTload`/`NIiter` pair assumes a sparse ADT with fast structural clear, partial pivoting tolerances (`CKTpivotAbsTol`, `CKTpivotRelTol`, [Source: src/include/ngspice/cktdefs.h#L198-L200]), and statistics hooks (`STATreorderTime`, `STATdecompTime`, `STATsolveTime`, [Source: src/maths/ni/niiter.c#L120-L187]).

## Interaction With Newton {#newton}

Within `NIiter`, the matrix phase branches:

- If `NIDIDPREORDER` is not set, run `SMPpreOrder` once ([Source: src/maths/ni/niiter.c#L103-L114]).
- When `NISHOULDREORDER` is set, call `SMPreorder` with pivot tolerances and `CKTdiagGmin` ([Source: src/maths/ni/niiter.c#L120-L139]); on failure, `SMPgetError` + `NODENAME` emit a warning naming two suspect nodes ([Source: src/maths/ni/niiter.c#L127-L131]).
- Otherwise call `SMPluFac` for incremental refactor ([Source: src/maths/ni/niiter.c#L141-L161]).

Thus sparsity exploitation is not an optional post-processing step—it is on the hot path of every Newton iteration.

## Numerical Invariants {#invariants}

| Invariant | Specification | Source |
|-----------|---------------|--------|
| Matrix cleared each load | `SMPclear` inside `CKTload` before stamping | [Source: src/spicelib/analysis/cktload.c#L56] (see [MNA section](02_modified_nodal_analysis_mna.md)) |
| Pivot thresholds | Uses `CKTpivotAbsTol`, `CKTpivotRelTol`, `CKTdiagGmin` during reorder/factor | [Source: src/maths/ni/niiter.c#L122-L143] |
| Singular recovery | `E_SINGULAR` from `SMPluFac` sets `NISHOULDREORDER` and retries loop | [Source: src/maths/ni/niiter.c#L146-L151] |

## Source Files {#source-files}

- **`src/include/ngspice/cktdefs.h`** — `CKTmatrix`, pivot tolerances.
- **`src/maths/ni/niiter.c`** — preorder, factor, solve orchestration.

## Related Chapters {#related-chapters}

- [Sparse matrix data structure](../06_sparse_solver/01_sparse_matrix_data_structure.md)
- [Sparse LU factorization](../06_sparse_solver/02_sparse_lu_factorization.md)
- [NIiter anatomy](../02_numerical_kernel_core/02_newton_raphson_iteration_niiter.md)

## Canonical Chains {#canonical-chains}

- `sparse_solve_chain` — factor + solve around `SMPluFac` / `SMPsolve`.

## Glossary {#glossary}

- **SMPmatrix** — ngspice sparse matrix handle; see [Numerical kernel terms](../24_glossary/01_numerical_kernel_terms.md#numerical-kernel-terms).
