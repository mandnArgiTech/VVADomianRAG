---
title: "NodalAI overview and scope"
chapter: "22_nodalai_kernel_reimplementation"
section: "01_nodalai_overview_and_scope"
section_number: "22.1"
topic: "nodalai_overview_and_scope"
mission_primary: "kernel_reimplementation"
mission_secondary: ["circuit_design_validation"]
related_files:
  - "src/include/ngspice/cktdefs.h"
  - "src/maths/ni/niiter.c"
  - "src/spicelib/analysis/cktload.c"
related_chapters:
  - "../00_foundations/06_dual_mission_reading_guide.md"
  - "../02_numerical_kernel_core/02_newton_raphson_iteration_niiter.md"
  - "../23_canonical_chains_reference/01_dc_operating_point_chain.md"
domain_concepts:
  - "kernel_reimplementation"
canonical_chain_tags:
  - "dc_operating_point_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 12
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# NodalAI overview and scope {#nodalai-overview-and-scope}

## What “NodalAI kernel reimplementation” means here {#what-it-means}

This book’s **kernel reimplementation** mission (see dual-mission framing in [chapter 00](../00_foundations/06_dual_mission_reading_guide.md)) treats ngspice as a **reference oracle**: a second implementation should reproduce the same **Modified Nodal Analysis (MNA) formulation**, **Newton–Raphson driver**, **device Jacobian stamping rules**, and **sparse direct solve semantics** closely enough that representative netlists match within numerical tolerance.

The on-chip loop is anchored in `NIiter`, which repeatedly loads the Jacobian and RHS until convergence or iteration limit ([Source: src/maths/ni/niiter.c#L29]). Each pass relies on `CKTload` to invoke every device’s `DEVload` through the `DEVices[]` table ([Source: src/spicelib/analysis/cktload.c#L61-L75], [Source: src/include/ngspice/devdefs.h#L47-L120]).

## In-scope artifacts {#in-scope}

- **Equation assembly:** nodal KCL, controlled-source bookkeeping, dynamic device branches as exposed through `CKTload`.
- **Nonlinear solve:** damping, limiting hooks, convergence tests (`NIconvTest` family), iteration caps.
- **Linear algebra:** sparse LU factor + solve (or a plug-in with identical pivoting tolerances if you deliberately match KLU).
- **Analysis drivers:** at minimum DCOP and transient, because they stress the same kernel with different `CKTmode` bits.

## Out-of-scope or deferrable {#out-of-scope}

- **Full frontend parity** (nutmeg scripting, every dot-card) unless your product needs it; embedders may target `sharedspice.c` instead.
- **Bit-identical floating point** across platforms; aim for tight tolerances on golden netlists, not memcpy-level reproducibility.

## How to use Part VI with Part VII {#how-to-use}

- Read a **canonical chain** in [chapter 23](../23_canonical_chains_reference/README.md) end-to-end, then map each stage to your module boundaries.
- Use [chapter 21](../21_validation_with_regression_suite/README.md) to lock regressions once a milestone passes the same `.cir`/`.out` pairs.
