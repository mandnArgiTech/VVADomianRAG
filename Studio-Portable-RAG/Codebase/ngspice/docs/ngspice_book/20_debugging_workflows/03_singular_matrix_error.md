---
title: "Singular matrix error"
chapter: "20_debugging_workflows"
section: "03_singular_matrix_error"
section_number: "20.3"
topic: "03_singular_matrix_error"
mission_primary: "circuit_design_validation"
mission_secondary: ["kernel_reimplementation"]
related_files:
  - "src/maths/sparse/spfactor.c"
related_chapters:
  - "../02_numerical_kernel_core/07_matrix_singularity_handling.md"
domain_concepts:
  - "singular_jacobian"
canonical_chain_tags:
  - "sparse_solve_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 10
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Singular matrix error {#singular-matrix-error}

## Sparse factor {#sparse-factor}

`spFactor` returns `MatrixIsSingular` when partial pivoting cannot find a usable pivot—comments throughout `spfactor.c` mark the detection paths ([Source: src/maths/sparse/spfactor.c#L303], [Source: src/maths/sparse/spfactor.c#L425-L449]).

## Common netlist causes {#causes}

- Floating nodes (missing DC path to ground).
- Perfect voltage loops without series resistance.
- Duplicate equations from malformed controlled sources.

## Mitigations {#mitigations}

Add tiny shunt resistors (`GMIN` already helps), fix topology, or inspect `CKTpivotAbsTol`/`CKTpivotRelTol` on `CKTcircuit` ([Source: src/include/ngspice/cktdefs.h#L199-L201]).
