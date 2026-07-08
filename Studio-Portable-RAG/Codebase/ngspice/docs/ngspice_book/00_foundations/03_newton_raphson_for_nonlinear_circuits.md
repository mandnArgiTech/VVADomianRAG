---
title: "Newton-Raphson for nonlinear circuits"
chapter: "00_foundations"
section: "03_newton_raphson_for_nonlinear_circuits"
section_number: "0.3"
topic: "03_newton_raphson_for_nonlinear_circuits"
mission_primary: "kernel_reimplementation"
mission_secondary: ["circuit_design_validation"]
related_files:
  - "src/maths/ni/niiter.c"
  - "src/maths/ni/niconv.c"
  - "src/spicelib/analysis/cktload.c"
related_chapters:
  - "../02_numerical_kernel_core/02_newton_raphson_iteration_niiter.md"
  - "../02_numerical_kernel_core/03_convergence_test_anatomy.md"
  - "../04_convergence_aids/01_convergence_aid_ladder.md"
domain_concepts:
  - "newton_raphson"
  - "convergence_test"
canonical_chain_tags:
  - "dc_operating_point_chain"
numerical_invariants_introduced:
  - "newton_raphson_iteration"
  - "convergence_test"
glossary_terms_introduced:
  - "Newton-Raphson iteration"
audience:
  - "NodalAI reimplementer"
  - "advanced circuit designer"
estimated_reading_minutes: 12
last_updated_from_source_at: "2026-04-20T02:48:52Z"
---

# Newton-Raphson for nonlinear circuits {#newton-raphson-for-nonlinear-circuits}

## Overview {#overview}

Nonlinear devices (diodes, MOS, BJT, etc.) make the MNA equations **F(x)=0** nonlinear. ngspice solves them with a damped Newton-Raphson loop implemented in `NIiter`: each pass calls `CKTload` to rebuild the Jacobian and RHS, factors the sparse matrix, solves for the correction, updates the iterate, and optionally applies node damping before testing convergence via `NIconvTest` ([Source: src/maths/ni/niiter.c#L79-L219], [Source: src/maths/ni/niconv.c#L18-L65]).

<!-- source: src/maths/ni/niiter.c -->
<!-- source: src/maths/ni/niconv.c -->

## What This Section Does {#what-it-does}

Gives the textbook algorithm and maps each step to symbols you will see in Chapter 2: `CKTload`, `SMPreorder` / `SMPluFac`, `SMPsolve`, `NIconvTest`, and the `CKTrhs` / `CKTrhsOld` swap that stores successive iterates.

## Algorithm Sketch {#algorithm-sketch}

1. **Load** — `CKTload(ckt)` zeros RHS, clears `SMPmatrix`, and dispatches all `DEVload` functions ([Source: src/spicelib/analysis/cktload.c#L52-L75]).
2. **Factor** — First iteration may `SMPpreOrder`; reordering or LU factor follows depending on `CKTniState` ([Source: src/maths/ni/niiter.c#L103-L162]).
3. **Solve** — `SMPsolve` writes the solution into the RHS arrays ([Source: src/maths/ni/niiter.c#L184-L200]).
4. **Iterate limit** — Exceeding `maxIter` (clamped to ≥100, [Source: src/maths/ni/niiter.c#L45-L46, L202-L213]) yields `E_ITERLIM`.
5. **Convergence test** — For passes after the first successful load, if no device flagged nonconvergence (`CKTnoncon==0`), call `NIconvTest`; otherwise force another iteration ([Source: src/maths/ni/niiter.c#L215-L219]).
6. **`NIconvTest` math** — For each matrix row, compare `new` vs `old` RHS values with `tol = RELTOL * max(|old|,|new|) + (VNTOL for voltage nodes else ABSTOL)` ([Source: src/maths/ni/niconv.c#L37-L64]).

## Damping Footnote {#damping}

When `CKTnodeDamping` is enabled for DC/transient op, large voltage swings between iterates trigger a scalar `damp_factor` that blends `CKTrhs` and `CKTstate0` toward their previous values ([Source: src/maths/ni/niiter.c#L225-L250]). Chapter 2 expands this behavior.

## Numerical Invariants {#invariants}

| Invariant | Specification | Source |
|-----------|---------------|--------|
| Convergence tolerance (voltage) | `tol = CKTreltol * max(|old|,|new|) + CKTvoltTol` | [Source: src/maths/ni/niconv.c#L41-L44] |
| Convergence tolerance (other) | `tol = CKTreltol * max(|old|,|new|) + CKTabstol` | [Source: src/maths/ni/niconv.c#L53-L56] |
| Minimum NR iterations budget | `maxIter` raised to at least 100 | [Source: src/maths/ni/niiter.c#L45-L46] |

## Failure Modes {#failure-modes}

- **`E_ITERLIM`** — Too many Newton steps without `NIconvTest` success ([Source: src/maths/ni/niiter.c#L202-L213]).
- **Singular matrix** — `SMPluFac` may return `E_SINGULAR`, triggering forced reorder ([Source: src/maths/ni/niiter.c#L142-L160]).
- **Device-reported nonconvergence** — If any `DEVload` sets `CKTnoncon`, `NIiter` skips the algebraic convergence check for that pass ([Source: src/maths/ni/niiter.c#L215-L219]).

## Source Files {#source-files}

- **`src/maths/ni/niiter.c`** — `NIiter` main loop.
- **`src/maths/ni/niconv.c`** — `NIconvTest`.
- **`src/spicelib/analysis/cktload.c`** — Jacobian/RHS assembly.

## Related Chapters {#related-chapters}

- [NIiter anatomy](../02_numerical_kernel_core/02_newton_raphson_iteration_niiter.md)
- [Convergence test anatomy](../02_numerical_kernel_core/03_convergence_test_anatomy.md)
- [Convergence aid ladder](../04_convergence_aids/01_convergence_aid_ladder.md)

## Canonical Chains {#canonical-chains}

- `dc_operating_point_chain` — NR stage inside DCOP.
- `transient_step_chain` — NR inside each accepted transient timepoint.

## Glossary {#glossary}

- **Newton-Raphson iteration** — Linearize, solve, update loop. See [Numerical kernel terms](../24_glossary/01_numerical_kernel_terms.md#numerical-kernel-terms).
