---
title: "Frontend and circuit design terms"
chapter: "24_glossary"
section: "03_frontend_circuit_design_terms"
section_number: "24.3"
topic: "03_frontend_circuit_design_terms"
mission_primary: "circuit_design_validation"
mission_secondary: []
related_files:
  - "src/frontend/inp.c"
  - "src/spicelib/parser/inp2dot.c"
related_chapters:
  - "../14_netlist_grammar/README.md"
  - "../15_parser_and_expansion/README.md"
domain_concepts:
  - "glossary_frontend"
canonical_chain_tags:
  - "netlist_to_simulation_chain"
numerical_invariants_introduced: []
glossary_terms_introduced:
  - "inp_spsource"
  - "INP2dot"
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 11
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Frontend and circuit design terms {#frontend-circuit-design-terms}

## Deck {#deck}

Ordered list of SPICE cards read by `inp_spsource` / `inp_readall` ([Source: src/frontend/inp.c#L300-L324], [Source: src/frontend/inpcom.c#L485-L497]).

## Dot card {#dot-card}

Line beginning with `.` handled in parser passes—analysis directives route through `INP2dot` ([Source: src/spicelib/parser/inp2dot.c#L631-L727]).

## Nutmeg {#nutmeg}

Interactive command processor (`com_*`) layered on the same simulation core as batch mode ([Source: src/frontend/runcoms.c#L36-L41]).

## Control block {#control-block}

`.control` … `.endc` scripting region extracted before netlist elaboration ([Source: src/frontend/inp.c#L429-L460]).

## Regression golden {#regression-golden}

Paired `.cir`/`.out` files compared by `tests/bin/check.sh` ([Source: ../21_validation_with_regression_suite/01_regression_suite_organization.md]).
