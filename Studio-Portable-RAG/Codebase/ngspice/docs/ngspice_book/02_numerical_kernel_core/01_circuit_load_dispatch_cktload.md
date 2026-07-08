---
title: "Circuit load dispatch (CKTload)"
chapter: "02_numerical_kernel_core"
section: "01_circuit_load_dispatch_cktload"
section_number: "2.1"
topic: "01_circuit_load_dispatch_cktload"
mission_primary: "kernel_reimplementation"
mission_secondary: ["circuit_design_validation"]
related_files:
  - "src/spicelib/analysis/cktload.c"
  - "src/include/ngspice/devdefs.h"
related_chapters:
  - "../01_architecture_overview/04_function_pointer_dispatch.md"
  - "02_newton_raphson_iteration_niiter.md"
  - "../07_device_model_contract/03_devload_load_function.md"
domain_concepts:
  - "mna_modified_nodal_analysis"
canonical_chain_tags:
  - "device_load_dispatch_chain"
numerical_invariants_introduced:
  - "mna_matrix_assembly"
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 12
last_updated_from_source_at: "2026-04-09T03:39:07.072860+00:00"
---

# Circuit load dispatch (CKTload) {#circuit-load-dispatch-cktload}

## Overview {#overview}

`CKTload` is the only function every Newton iteration invokes to rebuild the sparse MNA system. It clears RHS entries, wipes numeric matrix contents, walks all device types, and—during DC operating-point phases—applies `.nodeset` / `.ic` constraints as modified rows ([Source: src/spicelib/analysis/cktload.c#L29-L163]).

<!-- source: src/spicelib/analysis/cktload.c -->

## What This Module Does {#what-it-does}

`CKTload` answers: “Given the current `CKTmode`, device internal states, and node voltages encoded in RHS vectors, what linearized Jacobian and residual should the sparse solver see next?” It never solves the system; it only fills it.

## Algorithm In Detail {#algorithm}

1. **Timer start** — Accounts load time into `STATloadTime` ([Source: src/spicelib/analysis/cktload.c#L51-L52, L162-L163]).
2. **RHS zero** — For `i = 0 .. SMPmatSize`, `CKTrhs[i] = 0` ([Source: src/spicelib/analysis/cktload.c#L52-L55]).
3. **Matrix clear** — `SMPclear(ckt->CKTmatrix)` removes previous numeric fills while retaining sparsity pattern ([Source: src/spicelib/analysis/cktload.c#L56]).
4. **Device dispatch** — For each `i`, if `DEVices[i]`, `DEVload`, and `ckt->CKThead[i]` exist, invoke `DEVload` ([Source: src/spicelib/analysis/cktload.c#L61-L75]). Non-zero return aborts immediately.
5. **XSPICE maintenance** — When compiled in, clears MIF init flags and optionally applies `rshunt` conductance to selected diagonals ([Source: src/spicelib/analysis/cktload.c#L78-L101]).
6. **DC nodesets / ICs** — Under `MODEDC`, may overwrite rows/RHS for `.nodeset` and (during `MODETRANOP` without `MODEUIC`) `.ic` ([Source: src/spicelib/analysis/cktload.c#L104-L157]).

## Numerical Invariants {#invariants}

| Invariant | Specification | Source |
|-----------|---------------|--------|
| Fresh assembly | RHS cleared entirely before stamping | [Source: src/spicelib/analysis/cktload.c#L52-L55] |
| Pattern reuse | `SMPclear` preserves structural sparsity while zeroing values | [Source: src/spicelib/analysis/cktload.c#L56] |
| Device ordering | Deterministic loop `0 .. DEVmaxnum-1` | [Source: src/spicelib/analysis/cktload.c#L61] |

## Failure Modes {#failure-modes}

- Any `DEVload` error code propagates untouched ([Source: src/spicelib/analysis/cktload.c#L73-L74]).
- `CKTnoncon` may be raised by devices; `CKTload` resets `CKTtroubleNode` when that happens ([Source: src/spicelib/analysis/cktload.c#L64-L65]).

## Source Files {#source-files}

- **`src/spicelib/analysis/cktload.c`** — `CKTload`, `ZeroNoncurRow` helper for nodeset/ic handling ([Source: src/spicelib/analysis/cktload.c#L166-L180]).

## Diagrams {#diagrams}

```mermaid
flowchart TD
    A[CKTload entry] --> B[Zero CKTrhs]
    B --> C[SMPclear matrix]
    C --> D[For each device type i]
    D --> E{DEVload && CKThead[i]?}
    E -->|Yes| F[DEVices[i]->DEVload]
    E -->|No| D
    F --> G{error?}
    G -->|Yes| H[Return error]
    G -->|No| D
    D --> I[Optional XSPICE / rshunt]
    I --> J[Optional DC nodeset/ic]
    J --> K[Return OK]
```

## Related Chapters {#related-chapters}

- [Function pointer dispatch](../01_architecture_overview/04_function_pointer_dispatch.md)
- [NIiter](02_newton_raphson_iteration_niiter.md)
- [DEVload](../07_device_model_contract/03_devload_load_function.md)

## Canonical Chains {#canonical-chains}

- `device_load_dispatch_chain`
- `dc_operating_point_chain`
