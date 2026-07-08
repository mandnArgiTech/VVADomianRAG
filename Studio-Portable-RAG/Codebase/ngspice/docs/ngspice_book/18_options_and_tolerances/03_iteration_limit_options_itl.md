---
title: "Iteration limit options (ITL)"
chapter: "18_options_and_tolerances"
section: "03_iteration_limit_options_itl"
section_number: "18.3"
topic: "03_iteration_limit_options_itl"
mission_primary: "circuit_design_validation"
mission_secondary: ["kernel_reimplementation"]
related_files:
  - "src/include/ngspice/cktdefs.h"
  - "src/maths/ni/niiter.c"
related_chapters:
  - "../04_convergence_aids/05_itl_iteration_limit_options.md"
domain_concepts:
  - "itl_limits"
canonical_chain_tags: []
numerical_invariants_introduced:
  - "itl1_itl2_itl4"
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 10
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Iteration limit options (ITL) {#iteration-limit-options-itl}

## Field mapping {#field-mapping}

`CKTdcMaxIter` (ITL1), `CKTdcTrcvMaxIter` (ITL2), and `CKTtranMaxIter` (ITL4) bound Newton loops for DC, DC sweep inner solves, and transient timepoints respectively ([Source: src/include/ngspice/cktdefs.h#L187-L192]).

## Enforcement {#enforcement}

`NIiter` receives `maxIter` from callers such as `CKTop` / analysis drivers, so changing ITL values directly alters the loop bound ([Source: src/maths/ni/niiter.c#L29]).

## Debugging {#debugging}

Raising ITL without fixing ill-conditioned circuits usually masks singularities—pair limit changes with `CKTtroubleNode` diagnostics ([Source: src/include/ngspice/cktdefs.h#L259-L260]).
