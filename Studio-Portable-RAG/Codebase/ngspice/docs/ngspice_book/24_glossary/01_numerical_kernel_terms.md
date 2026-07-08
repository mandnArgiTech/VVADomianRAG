---
title: "Numerical kernel terms"
chapter: "24_glossary"
section: "01_numerical_kernel_terms"
section_number: "24.1"
topic: "01_numerical_kernel_terms"
mission_primary: "circuit_design_validation"
mission_secondary: ["kernel_reimplementation"]
related_files:
  - "src/maths/ni/niiter.c"
  - "src/spicelib/analysis/cktload.c"
  - "src/include/ngspice/cktdefs.h"
related_chapters:
  - "../02_numerical_kernel_core/README.md"
domain_concepts:
  - "glossary_numerical"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced:
  - "NIiter"
  - "CKTload"
  - "CKTcircuit"
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 12
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Numerical kernel terms {#numerical-kernel-terms}

## Modified Nodal Analysis (MNA) {#mna}

Stamp-based formulation assembling KCL rows and branch equations into one sparse system; ngspice stores tolerances and mode bits on `CKTcircuit` ([Source: src/include/ngspice/cktdefs.h#L198-L235]).

## Newton–Raphson iteration (`NIiter`) {#niiter}

Primary nonlinear solve loop invoked with an iteration cap (`maxIter`) ([Source: src/maths/ni/niiter.c#L29]).

## Circuit load (`CKTload`) {#cktload}

Dispatches each device type’s `DEVload` to fill Jacobian and RHS ([Source: src/spicelib/analysis/cktload.c#L61-L74]).

## Convergence test {#convergence-test}

`NIconvTest` (family) compares updates against `CKTreltol`, `CKTabstol`, `CKTvoltTol`, `CKTchgtol` ([Source: src/include/ngspice/cktdefs.h#L198-L203], [Source: ../02_numerical_kernel_core/03_convergence_test_anatomy.md]).

## Sparse LU {#sparse-lu}

Direct solve via `spFactor` / `spSolve` on the MNA matrix ([Source: ../06_sparse_solver/02_sparse_lu_factorization.md]).

## Local truncation error (LTE) {#lte}

Estimated using device `DEVtrunc` hooks and transient driver logic ([Source: ../05_numerical_integration/05_lte_estimation_devtrunc.md]).
