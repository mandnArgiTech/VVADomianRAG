---
title: "Matrix singularity handling"
chapter: "02_numerical_kernel_core"
section: "07_matrix_singularity_handling"
section_number: "2.7"
topic: "07_matrix_singularity_handling"
mission_primary: "kernel_reimplementation"
mission_secondary: ["circuit_design_validation"]
related_files:
  - "src/maths/ni/niiter.c"
related_chapters:
  - "02_newton_raphson_iteration_niiter.md"
  - "../06_sparse_solver/03_partial_pivoting_strategy.md"
domain_concepts:
  - "sparse_lu_factorization"
canonical_chain_tags:
  - "sparse_solve_chain"
numerical_invariants_introduced:
  - "sparse_partial_pivoting"
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 9
last_updated_from_source_at: "2026-04-20T02:48:52Z"
---

# Matrix singularity handling {#matrix-singularity-handling}

## Overview {#overview}

During `NIiter`, singularity can appear either during full reorder (`SMPreorder`) or incremental factorization (`SMPluFac`). The code distinguishes these paths: a failed reorder queries `SMPgetError` and prints the two matrix indices / node names involved ([Source: src/maths/ni/niiter.c#L127-L131]). An `E_SINGULAR` result from `SMPluFac` instead sets `NISHOULDREORDER` and retries the loop without surfacing immediately ([Source: src/maths/ni/niiter.c#L146-L151]).

<!-- source: src/maths/ni/niiter.c -->

## What This Section Does {#what-it-does}

Explains how ngspice recovers from bad pivots versus how it aborts when symbolic reordering itself fails—critical when porting the kernel to another sparse backend.

## Reorder Failures {#reorder}

```127:137:Studio-Portable-RAG/Codebase/ngspice/src/maths/ni/niiter.c
                    SMPgetError(ckt->CKTmatrix,&i,&j);
                    SPfrontEnd->IFerrorf (ERR_WARNING, "singular matrix:  check nodes %s and %s\n", NODENAME(ckt,i), NODENAME(ckt,j));
                    ...
                    return(error); /* can't handle these errors - pass up! */
```

Mission-2 agents should treat this warning as “structurally unsolvable MNA at this iterate” (floating nodes, missing reference, duplicate equations).

## Incremental Factor Failures {#lufac}

When `SMPluFac` returns `E_SINGULAR`, `NIiter` sets `NISHOULDREORDER` and `continue`s the outer loop, forcing a fresh reorder on the next pass ([Source: src/maths/ni/niiter.c#L146-L151]). This gives the pivot heuristic another chance after `CKTload` possibly changed diagonal dominance.

## Numerical Invariants {#invariants}

| Invariant | Specification | Source |
|-----------|---------------|--------|
| Pivot metadata | Reorder path uses `CKTpivotAbsTol`, `CKTpivotRelTol`, `CKTdiagGmin` | [Source: src/maths/ni/niiter.c#L122-L123] |
| Singular retry | `E_SINGULAR` from `SMPluFac` triggers reorder flag | [Source: src/maths/ni/niiter.c#L147-L150] |

## Source Files {#source-files}

- **`src/maths/ni/niiter.c`**

## Related Chapters {#related-chapters}

- [NIiter](02_newton_raphson_iteration_niiter.md)
- [Partial pivoting](../06_sparse_solver/03_partial_pivoting_strategy.md)

## Canonical Chains {#canonical-chains}

- `sparse_solve_chain`
