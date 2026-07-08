---
title: "Parameter substitution (numparam)"
chapter: "15_parser_and_expansion"
section: "04_parameter_substitution_numparam"
section_number: "15.4"
topic: "04_parameter_substitution_numparam"
mission_primary: "circuit_design_validation"
mission_secondary: []
related_files:
  - "src/frontend/numparam/numpaif.h"
  - "src/frontend/inpcom.c"
related_chapters:
  - "../14_netlist_grammar/10_dot_param_parameterization.md"
domain_concepts:
  - "numparam"
canonical_chain_tags:
  - "behavioral_source_eval_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 10
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Parameter substitution (numparam) {#parameter-substitution-numparam}

## Public interface {#public-interface}

`numpaif.h` exposes the hooks used from `subckt.c` and the deck copier: `nupa_copy`, `nupa_eval`, `nupa_scan`, dictionary maintenance, and `dynMaxckt` tracking expanded line counts ([Source: src/frontend/numparam/numpaif.h#L14-L25]).

## Pipeline placement {#pipeline}

`inp_readall` invokes `inp_fix_for_numparam` before whitespace cleanup, ensuring braces and expressions are in canonical form for evaluation ([Source: src/frontend/inpcom.c#L510]).

## Interaction with ASRC {#asrc}

Behavioral sources evaluate expression trees during `ASRCload`; numparam must have substituted numeric literals ahead of that pass ([Source: ../23_canonical_chains_reference/11_behavioral_source_eval_chain.md]).
