---
title: "Ordering heuristic"
chapter: "06_sparse_solver"
section: "04_ordering_heuristic"
section_number: "6.4"
topic: "04_ordering_heuristic"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/maths/sparse/spfactor.c"
related_chapters:
  - "02_sparse_lu_factorization.md"
domain_concepts:
  - "sparse_ordering_heuristic"
canonical_chain_tags:
  - "sparse_solve_chain"
numerical_invariants_introduced:
  - "sparse_ordering_heuristic"
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 7
last_updated_from_source_at: "2026-04-09T03:39:07.072860+00:00"
---

# Ordering heuristic {#ordering-heuristic}

## Overview {#overview}

`spOrderAndFactor` begins by deciding whether reordering is required (`Matrix->NeedsOrdering`). If not, it reuses the prior pivot sequence and only refactors ([Source: src/maths/sparse/spfactor.c#L255-L258]). Otherwise it executes the full Markowitz pivot search documented in the Sparse 1.3 module header ([Source: src/maths/sparse/spfactor.c#L1-L28]).

<!-- source: src/maths/sparse/spfactor.c -->

## Relationship to `NIiter` {#niiter}

`NIiter` toggles `NISHOULDREORDER` when junction initialization modes or singular factors demand a fresh ordering ([Source: src/maths/ni/niiter.c#L115-L118, L146-L151]).

## Source Files {#source-files}

- **`src/maths/sparse/spfactor.c`**

## Canonical Chains {#canonical-chains}

- `sparse_solve_chain`
