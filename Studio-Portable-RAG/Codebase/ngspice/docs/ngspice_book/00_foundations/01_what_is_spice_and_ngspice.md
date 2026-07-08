---
title: "What is SPICE and ngspice"
chapter: "00_foundations"
section: "01_what_is_spice_and_ngspice"
section_number: "0.1"
topic: "01_what_is_spice_and_ngspice"
mission_primary: "circuit_design_validation"
mission_secondary: ["kernel_reimplementation"]
related_files:
  - "src/spicelib/devices/cktinit.c"
  - "src/include/ngspice/cktdefs.h"
related_chapters:
  - "../01_architecture_overview/01_layered_architecture.md"
  - "../02_numerical_kernel_core/01_circuit_load_dispatch_cktload.md"
domain_concepts:
  - "mna_modified_nodal_analysis"
  - "newton_raphson"
canonical_chain_tags:
  - "dc_operating_point_chain"
numerical_invariants_introduced: []
glossary_terms_introduced:
  - "CKTcircuit"
audience:
  - "new circuit designer"
  - "NodalAI reimplementer"
  - "advanced circuit designer"
estimated_reading_minutes: 10
last_updated_from_source_at: "2026-04-09T03:39:07.069653+00:00"
---

# What is SPICE and ngspice {#what-is-spice-and-ngspice}

## Overview {#overview}

SPICE (Simulation Program with Integrated Circuit Emphasis) is a family of circuit simulators that formulate circuit equations in the time and frequency domains, solve them numerically, and report branch voltages, currents, and derived quantities. ngspice is an open-source descendant of Berkeley SPICE 3, extended with modern device models, optional mixed-signal (XSPICE) hooks, and both interactive and batch interfaces.

At runtime, every ngspice analysis operates on a single central object, `CKTcircuit`, which owns the sparse MNA matrix, right-hand side vectors, node list, integration state, and tolerances. The structure is defined in the public header and allocated by `CKTinit` ([Source: src/include/ngspice/cktdefs.h#L61-L291], [Source: src/spicelib/devices/cktinit.c#L24-L66]).

<!-- source: src/include/ngspice/cktdefs.h -->
<!-- source: src/spicelib/devices/cktinit.c -->

## What This Section Does {#what-it-does}

This section orients readers who may only know SPICE as a netlist language: it names the *mathematical* objects (MNA, Newton iteration, sparse solve) that the rest of the book traces in C. It deliberately stays high level; the next sections deepen MNA, Newton-Raphson, sparsity, and transient integration.

## How ngspice Fits the SPICE Tradition {#spice-tradition}

1. **Netlist in, equations out** — Devices contribute stamps to a shared linear system each Newton iteration; nonlinear devices linearize around the current iterate ([Source: src/spicelib/analysis/cktload.c#L61-L75]).
2. **Modified Nodal Analysis** — Unknowns include node voltages and selected branch currents; `CKTnode` distinguishes voltage (`SP_VOLTAGE`) and current (`SP_CURRENT`) rows ([Source: src/include/ngspice/cktdefs.h#L37-L53]).
3. **Iterative DC and inner transient solve** — The kernel repeatedly loads the Jacobian/RHS, factors the sparse matrix, updates the solution, and tests convergence (`NIiter`, covered in [Chapter 2](../02_numerical_kernel_core/02_newton_raphson_iteration_niiter.md)).

## Defaults Users Inherit {#defaults}

Even before reading `.options`, a new circuit receives classical SPICE-scale tolerances and iteration caps from `CKTinit`: for example `CKTreltol = 1e-3`, `CKTabstol = 1e-12`, `CKTvoltTol = 1e-6`, `CKTchgtol = 1e-14`, with `CKTdcMaxIter = 100`, `CKTdcTrcvMaxIter = 50`, and `CKTtranMaxIter = 10` ([Source: src/spicelib/devices/cktinit.c#L48-L65]). These fields are what `NIconvTest` and analysis drivers actually read at run time.

## Mission Mapping {#mission-mapping}

| Mission | Use this section to… |
|--------|----------------------|
| Circuit design / validation | Understand that netlist elements are not “magic”: they are coupled through `CKTload` and shared tolerances. |
| Kernel reimplementation | Name the persistent state object (`CKTcircuit`) every subsystem mutates; follow pointers into Chapters 1–2. |

## Source Files {#source-files}

- **`src/include/ngspice/cktdefs.h`** — `CKTcircuit`, `CKTnode`, mode flags, tolerance fields.
- **`src/spicelib/devices/cktinit.c`** — `CKTinit`: allocation and default tolerances / iteration limits / integration method.

## Related Chapters {#related-chapters}

- [Layered architecture](../01_architecture_overview/01_layered_architecture.md) — where `CKTcircuit` sits between frontend and devices.
- [MNA foundation](02_modified_nodal_analysis_mna.md) — equation view of the same structures.
- [CKTload dispatch](../02_numerical_kernel_core/01_circuit_load_dispatch_cktload.md) — per-device stamping.

## Canonical Chains {#canonical-chains}

- `dc_operating_point_chain` — end-to-end path from parsed netlist to converged DC (`rag_index.json`).

## Glossary {#glossary}

- **CKTcircuit** — Root simulator state: matrix, RHS, nodes, modes, tolerances. See [Numerical kernel terms](../24_glossary/01_numerical_kernel_terms.md#numerical-kernel-terms).
