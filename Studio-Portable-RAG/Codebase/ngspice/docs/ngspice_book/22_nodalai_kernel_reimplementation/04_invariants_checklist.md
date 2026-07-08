---
title: "Invariants checklist"
chapter: "22_nodalai_kernel_reimplementation"
section: "04_invariants_checklist"
section_number: "22.4"
topic: "invariants_checklist"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/maths/ni/niconv.c"
  - "src/maths/ni/niiter.c"
  - "src/include/ngspice/cktdefs.h"
related_chapters:
  - "../02_numerical_kernel_core/03_convergence_test_anatomy.md"
  - "../18_options_and_tolerances/02_tolerance_options_reltol_abstol_vntol_chgtol.md"
domain_concepts:
  - "numerical_invariants"
canonical_chain_tags: []
numerical_invariants_introduced:
  - "reltol_abstol_vntol"
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 10
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Invariants checklist {#invariants-checklist}

## Per-iteration Newton invariants {#newton}

| Invariant | Where enforced | Note |
|-----------|----------------|------|
| Max NR iterations | `NIiter(..., maxIter)` ([Source: src/maths/ni/niiter.c#L29]) | Must match `ITL1`/`ITL2` mapping from options |
| Convergence test | `NIconvTest` path | Voltages/currents/charges vs `RELTOL`/`ABSTOL`/… ([Source: ../02_numerical_kernel_core/03_convergence_test_anatomy.md]) |
| Damping / limiting | `DEVlimit`, junction helpers | Prevents exponential overflow in PN devices |

## Matrix invariants {#matrix}

- **Structural symmetry** for RLC without magnetics quirks; unsymmetric blocks appear with controlled sources and some charge models.
- **Ground reference** — one datum node; singular systems should match ngspice’s diagnostics ([Source: ../20_debugging_workflows/03_singular_matrix_error.md]).

## Transient extras {#transient}

- LTE norms and `DEVtrunc` hooks must agree before timestep policies match ([Source: ../05_numerical_integration/05_lte_estimation_devtrunc.md]).
