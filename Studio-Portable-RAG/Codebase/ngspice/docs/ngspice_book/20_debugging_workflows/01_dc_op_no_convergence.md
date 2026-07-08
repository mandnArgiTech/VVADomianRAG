---
title: "DC OP does not converge"
chapter: "20_debugging_workflows"
section: "01_dc_op_no_convergence"
section_number: "20.1"
topic: "01_dc_op_no_convergence"
mission_primary: "circuit_design_validation"
mission_secondary: []
related_files:
  - "src/spicelib/analysis/cktop.c"
  - "src/maths/ni/niiter.c"
related_chapters:
  - "../04_convergence_aids/01_convergence_aid_ladder.md"
domain_concepts:
  - "dc_convergence_debug"
canonical_chain_tags:
  - "convergence_failure_diagnosis_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 11
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# DC OP does not converge {#dc-op-no-convergence}

## What happens {#what-happens}

`CKTop` first calls `NIiter`; if it fails, gmin stepping (`dynamic_gmin` / `spice3_gmin`) and then source stepping (`gillespie_src` / `spice3_src`) execute based on `CKTnumGminSteps` / `CKTnumSrcSteps` ([Source: src/spicelib/analysis/cktop.c#L33-L72]).

## Instrumentation {#instrumentation}

Check `CKTtroubleNode` / `CKTtroubleElt` after failure—the fields identify the worst device or node for logging ([Source: src/include/ngspice/cktdefs.h#L259-L260]).

## User playbook {#playbook}

1. Verify nodesets / initial guesses.
2. Temporarily raise `GMIN` or enable stepping.
3. Simplify the nonlinear cluster (remove parasitics) to isolate the offending model.
