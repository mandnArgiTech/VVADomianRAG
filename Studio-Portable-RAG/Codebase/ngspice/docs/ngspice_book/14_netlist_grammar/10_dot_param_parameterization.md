---
title: ".param parameterization"
chapter: "14_netlist_grammar"
section: "10_dot_param_parameterization"
section_number: "14.10"
topic: "10_dot_param_parameterization"
mission_primary: "circuit_design_validation"
mission_secondary: []
related_files:
  - "src/spicelib/parser/inp2dot.c"
  - "src/frontend/numparam/xpressn.c"
related_chapters:
  - "../15_parser_and_expansion/04_parameter_substitution_numparam.md"
domain_concepts:
  - "param_directive"
canonical_chain_tags:
  - "netlist_to_simulation_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 9
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# .param parameterization {#dot-param-parameterization}

## Parser deferral {#deferral}

`INP2dot` explicitly skips `.param` lines during the analysis-construction pass—they are handled elsewhere in the frontend/numparam pipeline ([Source: src/spicelib/parser/inp2dot.c#L735-L738]).

## Evaluation model {#evaluation}

Parameterized expressions (`{...}`) and `B` sources ultimately bind through the expression machinery (`xpressn.c` and friends) described in [chapter 15](../15_parser_and_expansion/05_expression_evaluator.md).

## Authoring tips {#tips}

- Define `.param` **before** first use in the flattened deck order; expansion passes may not retroactively patch references.
- Prefer symbolic parameters for corners rather than hard-coded literals so `.step` and outer loops stay readable.
