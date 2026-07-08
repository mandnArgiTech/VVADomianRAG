---
title: ".subckt and .ends"
chapter: "14_netlist_grammar"
section: "09_dot_subckt_dot_ends"
section_number: "14.9"
topic: "09_dot_subckt_dot_ends"
mission_primary: "circuit_design_validation"
mission_secondary: ["kernel_reimplementation"]
related_files:
  - "src/frontend/subckt.c"
  - "src/spicelib/parser/inp2dot.c"
related_chapters:
  - "../15_parser_and_expansion/03_subcircuit_expansion_mechanics.md"
  - "../23_canonical_chains_reference/12_subcircuit_expansion_chain.md"
domain_concepts:
  - "subcircuits"
canonical_chain_tags:
  - "subcircuit_expansion_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 10
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# .subckt and .ends {#dot-subckt-dot-ends}

## Frontend expansion {#frontend-expansion}

Hierarchical netlists rely on `inp_subcktexpand`, which first collects `.subckt` definitions and then splices `X` instances with uniquified hierarchical node names ([Source: src/frontend/subckt.c#L42-L56], [Source: src/frontend/subckt.c#L209]).

## Parser stub history {#parser-stub}

`INP2dot` still contains a legacy branch that warns when `.subckt`/`.ends` appear during the `INP2dot` pass—modern flows expand subcircuits in the frontend before device parsing ([Source: src/spicelib/parser/inp2dot.c#L700-L704]). Treat that message as a sign the deck ordering is unexpected, not that subcircuits are unsupported.

## Modeling practice {#practice}

- Keep **port order** stable; formal-to-actual mapping is positional.
- Namespace collisions are avoided by prefixing each hierarchy level (`foo:bar:node` pattern described in `subckt.c` comments, [Source: src/frontend/subckt.c#L50-L52]).
