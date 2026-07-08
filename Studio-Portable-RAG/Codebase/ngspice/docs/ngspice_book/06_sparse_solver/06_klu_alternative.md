---
title: "KLU alternative"
chapter: "06_sparse_solver"
section: "06_klu_alternative"
section_number: "6.6"
topic: "06_klu_alternative"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "rag_index.json"
related_chapters:
  - "01_sparse_matrix_data_structure.md"
domain_concepts: []
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "ngspice core developer"
estimated_reading_minutes: 5
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# KLU alternative {#klu-alternative}

## Overview {#overview}

`rag_index.json` lists **KLU** as an optional, non-vendored faster sparse solver (`frameworks_libraries` entry). This source tree’s C corpus routes real solves through **Sparse 1.3** (`SMPluFac` → `spFactor`, `SMPsolve` → `spSolve`) as documented in Chapter 6.1–6.5.

## Repository State {#repo-state}

A repository-wide search for KLU-specific source files under `Studio-Portable-RAG/Codebase/ngspice/src` does not show an integrated KLU backend in this checkout. Treat KLU as a **build-time optional** not evidenced here.

## Source Files {#source-files}

- None in-tree for KLU; primary solver glue: `src/maths/sparse/spsmp.c`.

## Related Chapters {#related-chapters}

- [Sparse data structures](01_sparse_matrix_data_structure.md)
