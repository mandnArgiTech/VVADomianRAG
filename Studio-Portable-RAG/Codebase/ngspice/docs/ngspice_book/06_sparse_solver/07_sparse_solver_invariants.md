---
title: "Sparse solver invariants"
chapter: "06_sparse_solver"
section: "07_sparse_solver_invariants"
section_number: "6.7"
topic: "07_sparse_solver_invariants"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/maths/sparse/spsmp.c"
  - "src/maths/ni/niiter.c"
related_chapters:
  - "../02_numerical_kernel_core/08_kernel_invariants_summary.md"
domain_concepts:
  - "sparse_lu_factorization"
canonical_chain_tags:
  - "sparse_solve_chain"
numerical_invariants_introduced:
  - "sparse_lu_factorization"
  - "sparse_partial_pivoting"
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 8
last_updated_from_source_at: "2026-04-20T02:48:52Z"
---

# Sparse solver invariants {#sparse-solver-invariants}

## Must-Preserve Behaviors {#invariants}

| Invariant | Specification | Source |
|-----------|---------------|--------|
| GMIN injection on factor | `SMPluFac` / `SMPreorder` call `LoadGmin` before `spFactor` / `spOrderAndFactor` | [Source: src/maths/sparse/spsmp.c#L172-L174, L196-L199] |
| RHS/solution aliasing | `SMPsolve` passes the same pointer twice to `spSolve` | [Source: src/maths/sparse/spsmp.c#L232-L236] |
| Reorder vs refactor | `NIiter` chooses `SMPreorder` when `NISHOULDREORDER`, else `SMPluFac` | [Source: src/maths/ni/niiter.c#L120-L161] |
| Singular recovery | `E_SINGULAR` from `SMPluFac` sets reorder flag | [Source: src/maths/ni/niiter.c#L146-L151] |

## Source Files {#source-files}

- **`src/maths/sparse/spsmp.c`**
- **`src/maths/ni/niiter.c`**

## Related Chapters {#related-chapters}

- [Kernel invariants](../02_numerical_kernel_core/08_kernel_invariants_summary.md)

## Canonical Chains {#canonical-chains}

- `sparse_solve_chain`
