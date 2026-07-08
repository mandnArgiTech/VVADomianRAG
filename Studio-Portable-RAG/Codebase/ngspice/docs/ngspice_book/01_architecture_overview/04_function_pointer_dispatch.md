---
title: "Function pointer dispatch"
chapter: "01_architecture_overview"
section: "04_function_pointer_dispatch"
section_number: "1.4"
topic: "04_function_pointer_dispatch"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/spicelib/analysis/cktload.c"
  - "src/include/ngspice/devdefs.h"
related_chapters:
  - "../02_numerical_kernel_core/01_circuit_load_dispatch_cktload.md"
  - "../07_device_model_contract/03_devload_load_function.md"
domain_concepts:
  - "device_model_contract"
canonical_chain_tags:
  - "device_load_dispatch_chain"
numerical_invariants_introduced:
  - "mna_matrix_assembly"
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 8
last_updated_from_source_at: "2026-04-09T03:39:07.072860+00:00"
---

# Function pointer dispatch {#function-pointer-dispatch}

## Overview {#overview}

`CKTload` implements O(1) dispatch to an open-ended device set by indexing the global `DEVices[]` array and invoking `DEVload` when present:

```61:75:Studio-Portable-RAG/Codebase/ngspice/src/spicelib/analysis/cktload.c
    for (i = 0; i < DEVmaxnum; i++) {
        if (DEVices[i] && DEVices[i]->DEVload && ckt->CKThead[i]) {
            error = DEVices[i]->DEVload (ckt->CKThead[i], ckt);
            if (ckt->CKTnoncon)
                ckt->CKTtroubleNode = 0;
            ...
            if (error) return(error);
        }
    }
```

Each `DEVload` receives the head `GENmodel*` for that device type and the shared `CKTcircuit*`, stamping into the same `SMPmatrix` / RHS ([Source: src/include/ngspice/devdefs.h#L54-L55]).

<!-- source: src/spicelib/analysis/cktload.c -->
<!-- source: src/include/ngspice/devdefs.h -->

## What This Section Does {#what-it-does}

Documents the *exact* polymorphism mechanism SPICE3 uses—no virtual tables in the C++ sense, just arrays of function pointers.

## Numerical Invariants {#invariants}

| Invariant | Specification | Source |
|-----------|---------------|--------|
| Dispatch order | Deterministic increasing device index `0 .. DEVmaxnum-1` | [Source: src/spicelib/analysis/cktload.c#L61-L75] |
| Skip empty types | `CKThead[i]` must be non-NULL | [Source: src/spicelib/analysis/cktload.c#L62] |

## Failure Handling {#failure}

Any non-zero return from `DEVload` aborts `CKTload` immediately, propagating the error to `NIiter` ([Source: src/spicelib/analysis/cktload.c#L73-L74]).

## Source Files {#source-files}

- **`src/spicelib/analysis/cktload.c`**
- **`src/include/ngspice/devdefs.h`**

## Related Chapters {#related-chapters}

- [CKTload dispatch](../02_numerical_kernel_core/01_circuit_load_dispatch_cktload.md)
- [DEVload](../07_device_model_contract/03_devload_load_function.md)

## Canonical Chains {#canonical-chains}

- `device_load_dispatch_chain`
