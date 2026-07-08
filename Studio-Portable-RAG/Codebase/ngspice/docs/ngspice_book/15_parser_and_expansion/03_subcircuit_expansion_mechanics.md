---
title: "Subcircuit expansion mechanics"
chapter: "15_parser_and_expansion"
section: "03_subcircuit_expansion_mechanics"
section_number: "15.3"
topic: "03_subcircuit_expansion_mechanics"
mission_primary: "circuit_design_validation"
mission_secondary: []
related_files:
  - "src/frontend/subckt.c"
  - "src/frontend/inpcom.c"
related_chapters:
  - "../14_netlist_grammar/09_dot_subckt_dot_ends.md"
  - "../23_canonical_chains_reference/12_subcircuit_expansion_chain.md"
domain_concepts:
  - "subcircuit_flattening"
canonical_chain_tags:
  - "subcircuit_expansion_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 11
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Subcircuit expansion mechanics {#subcircuit-expansion-mechanics}

## Algorithm sketch {#algorithm}

`subckt.c` documents a two-pass approach: collect definitions, then expand `X` lines while rewriting node names with hierarchical prefixes ([Source: src/frontend/subckt.c#L42-L56]).

## Parameter integration {#parameters}

`inp_readall` calls `subckt_params_to_param` after fixing decks for numparam, ensuring `.param` inside subcircuits becomes visible to the expression engine ([Source: src/frontend/inpcom.c#L515-L517]).

## Model name translation {#models}

`modtranslate` / `devmodtranslate` helpers keep `.model` references coherent after copying bodies—critical when nested subcircuits reuse the same model label locally ([Source: src/frontend/subckt.c#L96-L97]).
