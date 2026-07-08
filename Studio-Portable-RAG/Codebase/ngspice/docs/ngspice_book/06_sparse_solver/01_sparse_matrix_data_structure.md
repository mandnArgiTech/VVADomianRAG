---
title: "Sparse matrix data structure"
chapter: "06_sparse_solver"
section: "01_sparse_matrix_data_structure"
section_number: "6.1"
topic: "01_sparse_matrix_data_structure"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/maths/sparse/spsmp.c"
related_chapters:
  - "../00_foundations/04_sparse_matrix_in_circuit_simulation.md"
domain_concepts:
  - "sparse_lu_factorization"
canonical_chain_tags:
  - "sparse_solve_chain"
numerical_invariants_introduced:
  - "mna_matrix_assembly"
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 9
last_updated_from_source_at: "2026-04-09T03:39:07.072860+00:00"
---

# Sparse matrix data structure {#sparse-matrix-data-structure}

## Overview {#overview}

ngspice’s `SMPmatrix` handle is a compatibility façade over **Sparse 1.3** (`spMatrix.h`). `SMPaddElt` / `SMPmakeElt` forward to `spGetElement`, and `SMPclear` calls `spClear` ([Source: src/maths/sparse/spsmp.c#L7-L31, L115-L147]).

The header comment documents the lineage: Sparse 1.3 replaced the original Spice3 SMP package for performance ([Source: src/maths/sparse/spsmp.c#L8-L12]).

<!-- source: src/maths/sparse/spsmp.c -->

## Source Files {#source-files}

- **`src/maths/sparse/spsmp.c`** — Spice3 API glue.
- **`src/maths/sparse/spmatrix.h`** / **`spdefs.h`** — internal matrix representation.

## Related Chapters {#related-chapters}

- [Sparse primer](../00_foundations/04_sparse_matrix_in_circuit_simulation.md)

## Canonical Chains {#canonical-chains}

- `sparse_solve_chain`
