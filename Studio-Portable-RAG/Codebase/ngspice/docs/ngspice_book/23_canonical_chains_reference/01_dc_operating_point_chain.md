---
title: "DC operating-point chain"
chapter: "23_canonical_chains_reference"
section: "01_dc_operating_point_chain"
section_number: "23.1"
topic: "dc_operating_point_chain"
mission_primary: "kernel_reimplementation"
mission_secondary: ["circuit_design_validation"]
related_files:
  - "src/frontend/inp.c"
  - "src/spicelib/devices/cktinit.c"
  - "src/spicelib/analysis/cktop.c"
  - "src/spicelib/analysis/dcop.c"
  - "src/maths/ni/niiter.c"
  - "src/spicelib/analysis/cktload.c"
  - "src/maths/sparse/spfactor.c"
  - "src/maths/sparse/spsolve.c"
  - "src/maths/ni/niconv.c"
related_chapters:
  - "../03_analysis_drivers/01_dc_operating_point_dcop.md"
  - "../02_numerical_kernel_core/02_newton_raphson_iteration_niiter.md"
domain_concepts:
  - "dc_operating_point"
canonical_chain_tags:
  - "dc_operating_point_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 10
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# DC operating-point chain {#dc-operating-point-chain}

## Summary {#summary}

End-to-end DCOP: parse → `CKTinit` → `DCop` → `CKTop`/`NIiter` → `CKTload`/`DEVload` → sparse factor/solve → `NIconvTest` → plot/export. Definition from `rag_index.json#canonical_chains` entry `dc_operating_point_chain`.

## Stages {#stages}

`netlist_parse` → `circuit_init` → `dcop_driver` → `nr_iteration` → `device_load` → `limiter_apply` → `matrix_factor` → `matrix_solve` → `convergence_test` → `result_export` ([Source: rag_index.json canonical chain object]).

## Canonical members {#members}

- `src/frontend/inp.c`, `src/spicelib/devices/cktinit.c`, `src/spicelib/analysis/cktop.c`, `src/spicelib/analysis/dcop.c`, `src/maths/ni/niiter.c`, `src/spicelib/analysis/cktload.c`, `src/maths/sparse/spfactor.c`, `src/maths/sparse/spsolve.c`, `src/maths/ni/niconv.c`

## Deep dives {#deep-dives}

- [DCop driver](../03_analysis_drivers/01_dc_operating_point_dcop.md)
- [NIiter](../02_numerical_kernel_core/02_newton_raphson_iteration_niiter.md)
- [CKTload](../02_numerical_kernel_core/01_circuit_load_dispatch_cktload.md)
