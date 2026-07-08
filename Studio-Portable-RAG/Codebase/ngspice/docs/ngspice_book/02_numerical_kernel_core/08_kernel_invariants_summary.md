---
title: "Kernel invariants summary"
chapter: "02_numerical_kernel_core"
section: "08_kernel_invariants_summary"
section_number: "2.8"
topic: "08_kernel_invariants_summary"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/maths/ni/niiter.c"
  - "src/maths/ni/niconv.c"
  - "src/spicelib/analysis/cktload.c"
  - "src/spicelib/devices/cktinit.c"
related_chapters:
  - "01_circuit_load_dispatch_cktload.md"
  - "02_newton_raphson_iteration_niiter.md"
  - "03_convergence_test_anatomy.md"
  - "../06_sparse_solver/07_sparse_solver_invariants.md"
domain_concepts:
  - "newton_raphson"
  - "convergence_test"
  - "mna_modified_nodal_analysis"
canonical_chain_tags:
  - "dc_operating_point_chain"
  - "sparse_solve_chain"
numerical_invariants_introduced:
  - "newton_raphson_iteration"
  - "convergence_test"
  - "mna_matrix_assembly"
  - "sparse_lu_factorization"
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 10
last_updated_from_source_at: "2026-04-20T02:48:52Z"
---

# Kernel invariants summary {#kernel-invariants-summary}

## Overview {#overview}

This section collects the “must not break” behaviors for anyone reimplementing ngspice’s Mission-1 loop: assembly, solve, convergence, and recovery. Each row points back to Chapter 2 sections with primary citations.

## Assembly Invariants {#assembly}

| Invariant | Why it matters | Section |
|-----------|----------------|---------|
| RHS zeroed before every `DEVload` pass | Prevents stale KCL residuals | [CKTload](01_circuit_load_dispatch_cktload.md) — [Source: src/spicelib/analysis/cktload.c#L52-L55] |
| `SMPclear` before stamping | Keeps Jacobian and RHS consistent | [CKTload](01_circuit_load_dispatch_cktload.md) — [Source: src/spicelib/analysis/cktload.c#L56] |
| Deterministic device order | Reproducibility across platforms | [CKTload](01_circuit_load_dispatch_cktload.md) — [Source: src/spicelib/analysis/cktload.c#L61] |

## Newton / Solve Invariants {#newton}

| Invariant | Why it matters | Section |
|-----------|----------------|---------|
| Minimum 100 NR iterations budget | Matches legacy expectation; avoids premature failure | [NIiter](02_newton_raphson_iteration_niiter.md) — [Source: src/maths/ni/niiter.c#L45-L46] |
| Reference node RHS zeroing | Ground equation must stay anchored | [NIiter](02_newton_raphson_iteration_niiter.md) — [Source: src/maths/ni/niiter.c#L198-L200] |
| Singular LU ⇒ reorder | Automatic recovery path | [Singularity](07_matrix_singularity_handling.md) — [Source: src/maths/ni/niiter.c#L146-L151] |

## Convergence Invariants {#convergence}

| Invariant | Why it matters | Section |
|-----------|----------------|---------|
| Voltage vs current tolerances | Units and magnitudes differ | [NIconvTest](03_convergence_test_anatomy.md) — [Source: src/maths/ni/niconv.c#L41-L56] |
| Device `CKTnoncon` short-circuits algebraic test | Devices may insist on extra iterations | [NIiter](02_newton_raphson_iteration_niiter.md) — [Source: src/maths/ni/niiter.c#L215-L219] |

## Default Numerics {#defaults}

`CKTinit` seeds `CKTreltol`, `CKTabstol`, `CKTvoltTol`, `CKTchgtol`, and iteration caps (`CKTdcMaxIter`, `CKTdcTrcvMaxIter`, `CKTtranMaxIter`) ([Source: src/spicelib/devices/cktinit.c#L48-L62]).

## Related Chapters {#related-chapters}

- [Sparse solver invariants](../06_sparse_solver/07_sparse_solver_invariants.md)
- [Device contract](../07_device_model_contract/README.md)

## Canonical Chains {#canonical-chains}

- `dc_operating_point_chain`, `transient_step_chain`, `sparse_solve_chain`, `device_load_dispatch_chain`
