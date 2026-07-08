---
title: "Damped Newton strategy"
chapter: "02_numerical_kernel_core"
section: "04_damped_newton_strategy"
section_number: "2.4"
topic: "04_damped_newton_strategy"
mission_primary: "kernel_reimplementation"
mission_secondary: ["circuit_design_validation"]
related_files:
  - "src/maths/ni/niiter.c"
  - "src/include/ngspice/cktdefs.h"
related_chapters:
  - "02_newton_raphson_iteration_niiter.md"
  - "../04_convergence_aids/01_convergence_aid_ladder.md"
domain_concepts:
  - "newton_raphson"
canonical_chain_tags:
  - "convergence_aid_chain"
numerical_invariants_introduced:
  - "newton_raphson_iteration"
glossary_terms_introduced:
  - "Node damping"
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 8
last_updated_from_source_at: "2026-04-20T02:48:52Z"
---

# Damped Newton strategy {#damped-newton-strategy}

## Overview {#overview}

Besides device-internal limiters, ngspice can apply **global node damping** when `CKTnodeDamping` is enabled for DC or operating-point analyses. After each solve, large voltage swings across iterations trigger a scalar `damp_factor` (bounded below by 0.1) that blends `CKTrhs` toward `CKTrhsOld` and likewise scales updates to `CKTstate0` using the saved vector `OldCKTstate0` ([Source: src/maths/ni/niiter.c#L225-L250]).

<!-- source: src/maths/ni/niiter.c -->

## What This Section Does {#what-it-does}

Documents the *outer* damping layer that operates on the full voltage vector—not the per-device `DEVpnjlim` / `DEVfetlim` hooks covered in Sections 2.5–2.6.

## Activation Conditions {#conditions}

Damping runs only when:

- `CKTnodeDamping != 0`
- `CKTnoncon != 0` (iteration still active)
- Mode includes `MODETRANOP` or `MODEDCOP`
- `iterno > 1`

([Source: src/maths/ni/niiter.c#L225-L227])

## Coefficient Selection {#coefficient}

For voltage nodes, track the maximum positive delta between new and old RHS; if it exceeds 10 V, set `damp_factor = 10/maxdiff`, then clamp to ≥0.1 ([Source: src/maths/ni/niiter.c#L228-L238]). Apply the same factor to all node voltages and state vector corrections ([Source: src/maths/ni/niiter.c#L240-L249]).

## Numerical Invariants {#invariants}

| Invariant | Specification | Source |
|-----------|---------------|--------|
| Minimum damping scale | `damp_factor` never below `0.1` once triggered | [Source: src/maths/ni/niiter.c#L237-L238] |
| State consistency | `CKTstate0` and `CKTrhs` use identical `damp_factor` | [Source: src/maths/ni/niiter.c#L240-L249] |

## Failure Modes {#failure-modes}

Damping improves robustness but can slow convergence; if combined with pathological devices, outer aids (`CKTop` GMIN stepping, etc.) may still be required—see [Convergence aid ladder](../04_convergence_aids/01_convergence_aid_ladder.md) and `dynamic_gmin` in `src/spicelib/analysis/cktop.c`.

## Source Files {#source-files}

- **`src/maths/ni/niiter.c`** — damping block inside `NIiter`.

## Related Chapters {#related-chapters}

- [NIiter](02_newton_raphson_iteration_niiter.md)
- [Convergence aid ladder](../04_convergence_aids/01_convergence_aid_ladder.md)
- [Junction limiting](05_voltage_limiting_devpnjlim.md)

## Glossary {#glossary}

- **Node damping** — Global scaling of NR updates; see [Numerical kernel terms](../24_glossary/01_numerical_kernel_terms.md#numerical-kernel-terms).
