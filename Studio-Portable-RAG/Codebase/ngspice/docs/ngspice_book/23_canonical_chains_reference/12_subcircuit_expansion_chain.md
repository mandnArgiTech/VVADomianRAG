---
title: "Subcircuit expansion chain"
chapter: "23_canonical_chains_reference"
section: "12_subcircuit_expansion_chain"
section_number: "23.12"
topic: "subcircuit_expansion_chain"
mission_primary: "circuit_design_validation"
mission_secondary: []
related_files:
  - "src/frontend/subckt.c"
  - "src/spicelib/parser/inpdomod.c"
related_chapters:
  - "../15_parser_and_expansion/03_subcircuit_expansion_mechanics.md"
  - "../14_netlist_grammar/09_dot_subckt_dot_ends.md"
domain_concepts:
  - "subcircuit_expansion"
canonical_chain_tags:
  - "subcircuit_expansion_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 8
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Subcircuit expansion chain {#subcircuit-expansion-chain}

## Summary {#summary}

`inp_subcktexpand` implements the classic two-phase flow: collect `.subckt` bodies, then splice `X` instances with uniquified hierarchical node names ([Source: src/frontend/subckt.c#L42-L56], [Source: src/frontend/subckt.c#L209]). Model name translation interacts with the model table built during parsing (`inpdomod.c`).

## Stages {#stages}

`subckt_parse` → `flatten` → `param_expand` ([Source: rag_index.json]).

## Canonical members {#members}

`src/frontend/subckt.c`, `src/spicelib/parser/inpdomod.c`

## Deep dives {#deep-dives}

- [Expansion mechanics](../15_parser_and_expansion/03_subcircuit_expansion_mechanics.md)
- [.subckt grammar](../14_netlist_grammar/09_dot_subckt_dot_ends.md)
