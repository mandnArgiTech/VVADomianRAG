---
title: "Modified nodal analysis (MNA)"
chapter: "00_foundations"
section: "02_modified_nodal_analysis_mna"
section_number: "0.2"
topic: "02_modified_nodal_analysis_mna"
mission_primary: "kernel_reimplementation"
mission_secondary: ["circuit_design_validation"]
related_files:
  - "src/include/ngspice/cktdefs.h"
  - "src/spicelib/analysis/cktload.c"
related_chapters:
  - "../02_numerical_kernel_core/01_circuit_load_dispatch_cktload.md"
  - "../06_sparse_solver/01_sparse_matrix_data_structure.md"
domain_concepts:
  - "mna_modified_nodal_analysis"
canonical_chain_tags:
  - "device_load_dispatch_chain"
numerical_invariants_introduced:
  - "mna_matrix_assembly"
glossary_terms_introduced:
  - "MNA stamp"
audience:
  - "NodalAI reimplementer"
  - "ngspice core developer"
estimated_reading_minutes: 12
last_updated_from_source_at: "2026-04-09T03:39:07.072860+00:00"
---

# Modified nodal analysis (MNA) {#modified-nodal-analysis-mna}

## Overview {#overview}

Modified Nodal Analysis expresses Kirchhoff’s laws as a sparse linear system **J · x = b** each Newton iteration: Jacobian **J** and right-hand side **b** accumulate contributions (“stamps”) from every device. ngspice keeps the global system in `SMPmatrix *CKTmatrix` and uses dense RHS slots `CKTrhs`, `CKTrhsOld`, and `CKTrhsSpare` for the current iterate, the previous iterate (convergence comparison), and solver temporaries ([Source: src/include/ngspice/cktdefs.h#L109-L118]).

<!-- source: src/include/ngspice/cktdefs.h -->
<!-- source: src/spicelib/analysis/cktload.c -->

## What This Section Does {#what-it-does}

It connects textbook MNA to ngspice data structures: how nodes become matrix indices, how voltage vs current unknowns are tagged, and how `CKTload` clears and refills the system each call.

## Nodes and Unknowns {#nodes-unknowns}

Each `CKTnode` carries `name`, `type` (`SP_VOLTAGE` or `SP_CURRENT`), `number` (row/column index), optional `.ic` / `.nodeset`, and a pointer into the matrix for diagonal entries ([Source: src/include/ngspice/cktdefs.h#L37-L53]). The ordered list `ckt->CKTnodes` is walked whenever the solver or diagnostics need human-readable names (`NODENAME` macro, [Source: src/include/ngspice/cktdefs.h#L154-L155]).

## Assembly Pattern in `CKTload` {#cktload-pattern}

`CKTload` implements the *global* assembly pass:

1. Zero the RHS up to matrix size ([Source: src/spicelib/analysis/cktload.c#L52-L55]).
2. Clear symbolic/numeric sparse structure via `SMPclear` ([Source: src/spicelib/analysis/cktload.c#L56]).
3. For each device type index `i`, if `DEVices[i]` exists, exposes `DEVload`, and the model list `ckt->CKThead[i]` is non-NULL, call `DEVices[i]->DEVload(ckt->CKThead[i], ckt)` ([Source: src/spicelib/analysis/cktload.c#L61-L75]).

Thus MNA stamping is delegated per device family while sharing one matrix and RHS layout—classic SPICE3 design.

## Numerical Invariants {#invariants}

| Invariant | Specification | Source |
|-----------|---------------|--------|
| RHS zeroed before stamp | `CKTrhs[0..size]` cleared each `CKTload` | [Source: src/spicelib/analysis/cktload.c#L52-L55] |
| Matrix cleared before stamp | `SMPclear(ckt->CKTmatrix)` precedes device loads | [Source: src/spicelib/analysis/cktload.c#L56] |
| Device participation | Only types with non-NULL `DEVload` and non-empty `CKThead[i]` load | [Source: src/spicelib/analysis/cktload.c#L61-L63] |

## DC Auxiliary Rows {#dc-aux}

When `CKTmode` indicates DC operating point work, `CKTload` may impose `.nodeset` and (for `MODETRANOP` without `MODEUIC`) `.ic` constraints by rewriting rows and RHS entries ([Source: src/spicelib/analysis/cktload.c#L104-L157]). This is still MNA—it replaces or scales rows to pin tentative voltages during Newton.

## Mathematical Form {#math}

Let **x** collect all MNA unknowns (node voltages and dependent branch currents). For nonlinear resistive devices, Newton linearization yields:

\[
J(x_k)\,\Delta x = -F(x_k), \qquad x_{k+1} = x_k + \Delta x
\]

`CKTload` builds the sparse structure and numeric values for \(J\) and \(F\) at \(x_k\); `NIiter` solves for \(\Delta x\) (see [Newton-Raphson section](03_newton_raphson_for_nonlinear_circuits.md) and [Chapter 2](../02_numerical_kernel_core/02_newton_raphson_iteration_niiter.md)).

## Source Files {#source-files}

- **`src/include/ngspice/cktdefs.h`** — `CKTcircuit`, `CKTnode`, matrix/RHS pointers.
- **`src/spicelib/analysis/cktload.c`** — `CKTload` driver and DC nodeset/ic hooks.

## Related Chapters {#related-chapters}

- [CKTload dispatch](../02_numerical_kernel_core/01_circuit_load_dispatch_cktload.md) — extended commentary on the same function.
- [Sparse matrix data structures](../06_sparse_solver/01_sparse_matrix_data_structure.md) — `SMPmatrix` representation.
- [SPICEdev contract](../01_architecture_overview/03_spicedev_plugin_contract.md) — why `DEVload` is the right abstraction.

## Canonical Chains {#canonical-chains}

- `device_load_dispatch_chain` — `CKTload` as the fan-out point for all `DEVload` implementations.

## Glossary {#glossary}

- **MNA stamp** — Local Jacobian/RHS contribution of one device instance into the global sparse system. See [Numerical kernel terms](../24_glossary/01_numerical_kernel_terms.md#numerical-kernel-terms).
