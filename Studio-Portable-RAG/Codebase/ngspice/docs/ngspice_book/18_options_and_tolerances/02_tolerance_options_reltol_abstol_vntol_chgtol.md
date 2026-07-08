---
title: "Tolerance options (RELTOL, ABSTOL, VNTOL, CHGTOL)"
chapter: "18_options_and_tolerances"
section: "02_tolerance_options_reltol_abstol_vntol_chgtol"
section_number: "18.2"
topic: "02_tolerance_options_reltol_abstol_vntol_chgtol"
mission_primary: "circuit_design_validation"
mission_secondary: ["kernel_reimplementation"]
related_files:
  - "src/include/ngspice/cktdefs.h"
  - "src/maths/ni/niconv.c"
related_chapters:
  - "../02_numerical_kernel_core/03_convergence_test_anatomy.md"
domain_concepts:
  - "convergence_tolerances"
canonical_chain_tags: []
numerical_invariants_introduced:
  - "reltol_abstol_vntol"
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 11
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Tolerance options (RELTOL, ABSTOL, VNTOL, CHGTOL) {#tolerance-options}

## Circuit fields {#circuit-fields}

`CKTcircuit` stores `CKTreltol`, `CKTabstol`, `CKTvoltTol`, and `CKTchgtol`, which `NIconvTest` consults when deciding whether Newton updates are small enough ([Source: src/include/ngspice/cktdefs.h#L198-L203], [Source: ../02_numerical_kernel_core/03_convergence_test_anatomy.md]).

## Usage guidance {#usage}

- Tighten `RELTOL` only when all models are well-scaled; otherwise you pay in NR iterations.
- `ABSTOL` dominates when branch currents approach zero (leakage-dominated CMOS).

## LTE cousins {#lte}

When `NEWTRUNC` is enabled, additional `CKTlteReltol` / `CKTlteAbstol` fields participate in truncation ([Source: src/include/ngspice/cktdefs.h#L205-L208]).
