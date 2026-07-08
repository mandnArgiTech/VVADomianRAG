---
title: "Convergence aid ladder"
chapter: "04_convergence_aids"
section: "01_convergence_aid_ladder"
section_number: "4.1"
topic: "01_convergence_aid_ladder"
mission_primary: "kernel_reimplementation"
mission_secondary: ["circuit_design_validation"]
related_files:
  - "src/spicelib/analysis/cktop.c"
related_chapters:
  - "../02_numerical_kernel_core/02_newton_raphson_iteration_niiter.md"
  - "../23_canonical_chains_reference/03_convergence_aid_chain.md"
domain_concepts:
  - "convergence_aids"
canonical_chain_tags:
  - "convergence_aid_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 10
last_updated_from_source_at: "2026-04-09T03:39:07.072860+00:00"
---

# Convergence aid ladder {#convergence-aid-ladder}

## Overview {#overview}

`CKTop` implements the DC convergence strategy:

1. Unless `CKTnoOpIter` is set, call `NIiter` with the supplied iteration limit ([Source: src/spicelib/analysis/cktop.c#L33-L45]).
2. If Newton fails (`converged != 0`), attempt **GMIN stepping** when `CKTnumGminSteps >= 1`, choosing `dynamic_gmin` vs `spice3_gmin` based on the step count ([Source: src/spicelib/analysis/cktop.c#L48-L59]).
3. If still failing, attempt **source stepping** when `CKTnumSrcSteps >= 1`, using `gillespie_src` or `spice3_src` ([Source: src/spicelib/analysis/cktop.c#L67-L72]).

<!-- source: src/spicelib/analysis/cktop.c -->

## Mission Mapping {#mission-mapping}

- **Reimplementers** must preserve ordering: NR first, then GMIN, then source scaling.
- **Designers** tune the same behavior through `.options gminsteps`, `srcsteps`, `noopiter`, etc. (wired in `cktsopt.c`, [Source: src/spicelib/analysis/cktsopt.c#L88-L96, L230-L250]).

## Source Files {#source-files}

- **`src/spicelib/analysis/cktop.c`**
- **`src/spicelib/analysis/cktsopt.c`** — option wiring for step counts.

## Related Chapters {#related-chapters}

- [NIiter](../02_numerical_kernel_core/02_newton_raphson_iteration_niiter.md)
- [GMIN stepping](02_gmin_stepping_mechanics.md)
- [Source stepping](03_source_stepping_mechanics.md)

## Canonical Chains {#canonical-chains}

- `convergence_aid_chain`
