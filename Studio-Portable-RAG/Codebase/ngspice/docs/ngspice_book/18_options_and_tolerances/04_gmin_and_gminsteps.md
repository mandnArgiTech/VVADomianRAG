---
title: "GMIN and GMINSTEPS"
chapter: "18_options_and_tolerances"
section: "04_gmin_and_gminsteps"
section_number: "18.4"
topic: "04_gmin_and_gminsteps"
mission_primary: "circuit_design_validation"
mission_secondary: ["kernel_reimplementation"]
related_files:
  - "src/include/ngspice/cktdefs.h"
  - "src/spicelib/analysis/cktop.c"
related_chapters:
  - "../04_convergence_aids/02_gmin_stepping_mechanics.md"
domain_concepts:
  - "gmin_stepping"
canonical_chain_tags:
  - "convergence_aid_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 10
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# GMIN and GMINSTEPS {#gmin-and-gminsteps}

## Conductance floor {#conductance-floor}

`CKTgmin`, `CKTgshunt`, and `CKTgminFactor` capture the minimum junction conductance and stepping ratios used during difficult DC solves ([Source: src/include/ngspice/cktdefs.h#L209-L222]).

## Stepping policy {#stepping-policy}

`CKTnumGminSteps` selects whether dynamic or Spice3-style gmin stepping runs when `NIiter` fails inside `CKTop` ([Source: src/include/ngspice/cktdefs.h#L220-L222], [Source: src/spicelib/analysis/cktop.c#L48-L57]).

## `CKTnoOpIter` {#noopiter}

Setting `CKTnoOpIter` skips the initial brute-force NR pass and jumps straight into gmin stepping—useful for highly nonlinear decks but risky for well-behaved linear circuits ([Source: src/include/ngspice/cktdefs.h#L233-L235]).
