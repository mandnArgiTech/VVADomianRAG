---
title: "Data structures: CKTcircuit"
chapter: "01_architecture_overview"
section: "02_data_structures_cktcircuit"
section_number: "1.2"
topic: "02_data_structures_cktcircuit"
mission_primary: "kernel_reimplementation"
mission_secondary: ["circuit_design_validation"]
related_files:
  - "src/include/ngspice/cktdefs.h"
  - "src/spicelib/devices/cktinit.c"
related_chapters:
  - "../00_foundations/02_modified_nodal_analysis_mna.md"
  - "../02_numerical_kernel_core/02_newton_raphson_iteration_niiter.md"
domain_concepts:
  - "mna_modified_nodal_analysis"
canonical_chain_tags:
  - "device_load_dispatch_chain"
numerical_invariants_introduced:
  - "mna_matrix_assembly"
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 14
last_updated_from_source_at: "2026-04-09T03:39:07.065678+00:00"
---

# Data structures: CKTcircuit {#data-structures-cktcircuit}

## Overview {#overview}

`CKTcircuit` is the persistent root state for one circuit under simulation: sparse matrix, RHS vectors, doubly-linked node list, multi-step integration history, mode flags, tolerances, and pointers into the device model graph (`CKThead`). The struct definition spans hundreds of lines because it aggregates *every* analysis subsystem ([Source: src/include/ngspice/cktdefs.h#L61-L291]).

`CKTinit` allocates the object, zeros model heads, and seeds defaults such as tolerances, iteration caps, and temperature ([Source: src/spicelib/devices/cktinit.c#L24-L75]).

<!-- source: src/include/ngspice/cktdefs.h -->
<!-- source: src/spicelib/devices/cktinit.c -->

## What This Section Does {#what-it-does}

Highlights the fields every reimplementer must reproduce— even if their Python classes use different names.

## Core Subsystems Inside `CKTcircuit` {#subsystems}

| Concern | Representative fields | Source |
|--------|-------------------------|--------|
| Device graph | `GENmodel **CKThead` sized to `DEVmaxnum` | [Source: src/include/ngspice/cktdefs.h#L70-L71] |
| Sparse MNA | `SMPmatrix *CKTmatrix` | [Source: src/include/ngspice/cktdefs.h#L109] |
| Newton state | `CKTrhs`, `CKTrhsOld`, `CKTrhsSpare`, `CKTniState` | [Source: src/include/ngspice/cktdefs.h#L110-L118, L130-L143] |
| Nodes | `CKTnode *CKTnodes`, `CKTlastNode` | [Source: src/include/ngspice/cktdefs.h#L151-L152] |
| Integration | `CKTstates[8]`, `CKTorder`, `CKTintegrateMethod` | [Source: src/include/ngspice/cktdefs.h#L79-L107] |
| Modes | `long CKTmode` with `MODEDC*`, `MODEINIT*` masks | [Source: src/include/ngspice/cktdefs.h#L158-L181] |
| Tolerances | `CKTreltol`, `CKTabstol`, `CKTvoltTol`, `CKTchgtol` | [Source: src/include/ngspice/cktdefs.h#L198-L203] |
| Iteration caps | `CKTdcMaxIter`, `CKTdcTrcvMaxIter`, `CKTtranMaxIter` | [Source: src/include/ngspice/cktdefs.h#L187-L192] |

## Node Records {#nodes}

`CKTnode` stores both voltage and current unknowns (`SP_VOLTAGE`, `SP_CURRENT`), the matrix index, optional `.ic` / `.nodeset`, and `ptr` into the sparse matrix for quick diagonal access ([Source: src/include/ngspice/cktdefs.h#L37-L53]).

## Initialization Contract {#init}

`CKTinit` must succeed before any stamping:

- Allocates `CKThead` array of length `DEVmaxnum` ([Source: src/spicelib/devices/cktinit.c#L34-L41]).
- Sets `CKTmatrix = NULL` until the matrix is built later ([Source: src/spicelib/devices/cktinit.c#L46]).
- Seeds physical and numerical defaults (`CKTtemp`, `CKTreltol`, etc., [Source: src/spicelib/devices/cktinit.c#L48-L75]).

## Numerical Invariants {#invariants}

| Invariant | Specification | Source |
|-----------|---------------|--------|
| Model slot initialization | Every `CKThead[i]` starts `NULL` | [Source: src/spicelib/devices/cktinit.c#L40-L41] |
| Default RELTOL / ABSTOL / VNTOL | `1e-3`, `1e-12`, `1e-6` | [Source: src/spicelib/devices/cktinit.c#L50-L53] |
| DC / sweep / tran iteration caps | `100 / 50 / 10` | [Source: src/spicelib/devices/cktinit.c#L60-L62] |

## Source Files {#source-files}

- **`src/include/ngspice/cktdefs.h`** — authoritative layout.
- **`src/spicelib/devices/cktinit.c`** — allocation + defaults.

## Related Chapters {#related-chapters}

- [MNA foundations](../00_foundations/02_modified_nodal_analysis_mna.md)
- [NIiter](../02_numerical_kernel_core/02_newton_raphson_iteration_niiter.md)

## Canonical Chains {#canonical-chains}

- `device_load_dispatch_chain` — uses `CKThead` + `CKTmatrix` together.
