---
title: "Options overview"
chapter: "18_options_and_tolerances"
section: "01_options_overview"
section_number: "18.1"
topic: "01_options_overview"
mission_primary: "circuit_design_validation"
mission_secondary: ["kernel_reimplementation"]
related_files:
  - "src/spicelib/parser/inpdoopt.c"
  - "src/include/ngspice/cktdefs.h"
related_chapters:
  - "../14_netlist_grammar/11_dot_options_directive.md"
domain_concepts:
  - "spice_options"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 10
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Options overview {#options-overview}

## Netlist path {#netlist-path}

`.options` lines become calls to `INPdoOpts`, which looks up each token in the simulator’s analysis-parameter table and applies values through `ft_sim->setAnalysisParm` ([Source: src/spicelib/parser/inpdoopt.c#L34-L68]).

## Runtime state {#runtime-state}

The authoritative floating-point controls (`CKTreltol`, `CKTabstol`, `CKTvoltTol`, `CKTchgtol`, …) live on `CKTcircuit` ([Source: src/include/ngspice/cktdefs.h#L198-L203]).

## Interaction map {#interaction-map}

| Category | See section |
|----------|-------------|
| Tolerances | [§2](02_tolerance_options_reltol_abstol_vntol_chgtol.md) |
| Iteration caps | [§3](03_iteration_limit_options_itl.md) |
| GMIN stepping | [§4](04_gmin_and_gminsteps.md) |
| Integration | [§5](05_method_options_trap_gear.md) |
