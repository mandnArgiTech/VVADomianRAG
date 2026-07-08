---
title: "Porting strategy layer by layer"
chapter: "22_nodalai_kernel_reimplementation"
section: "02_porting_strategy_layer_by_layer"
section_number: "22.2"
topic: "porting_strategy_layer_by_layer"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/maths/sparse/spsolve.c"
  - "src/maths/ni/niiter.c"
  - "src/spicelib/analysis/cktload.c"
  - "src/spicelib/devices/resistor/rsload.c"
related_chapters:
  - "../06_sparse_solver/README.md"
  - "../02_numerical_kernel_core/README.md"
  - "../08_passive_devices/01_resistor.md"
domain_concepts:
  - "incremental_porting"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 11
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Porting strategy layer by layer {#porting-strategy-layer-by-layer}

## Bottom-up ordering {#bottom-up}

1. **Sparse solve primitives** — Accept a static pattern, numeric factor, and RHS solve; match `spSolve` semantics ([Source: src/maths/sparse/spsolve.c#L127-L130]). Until stamping is correct, use hand-built tiny matrices.
2. **Newton driver shell** — Implement `NIiter`’s iterate/until-converged structure with a fake `CKTload` that fills a known Jacobian ([Source: src/maths/ni/niiter.c#L29]).
3. **Dispatch shell** — Replace the fake loader with `CKTload`’s `DEVices[i]->DEVload` loop ([Source: src/spicelib/analysis/cktload.c#L61-L74]).
4. **Devices** — Start with linear passives (resistor stamp) then add one nonlinear element (diode or MOS) once limiting and `NIconvTest` are wired.

## Milestones that catch real bugs {#milestones}

| Milestone | Pass criterion |
|-----------|----------------|
| M0 | Sparse solver matches reference on injected LU cases |
| M1 | `NIiter` converges on 2-node linear divider |
| M2 | Single nonlinear device IV curve matches ngspice sweep |
| M3 | Full `tests/regression` subset you care about |

## When to fork analysis drivers {#analysis-drivers}

Defer `DCop`/`DCtran` until the `CKTload` + `NIiter` pair is stable; drivers mostly set `CKTmode` and time-step policy ([Source: ../03_analysis_drivers/README.md]).
