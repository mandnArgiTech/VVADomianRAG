---
title: "Subcircuit design pattern"
chapter: "19_circuit_design_patterns"
section: "07_subcircuit_design_pattern"
section_number: "19.7"
topic: "07_subcircuit_design_pattern"
mission_primary: "circuit_design_validation"
mission_secondary: []
related_files:
  - "src/frontend/subckt.c"
related_chapters:
  - "../15_parser_and_expansion/03_subcircuit_expansion_mechanics.md"
domain_concepts:
  - "subckt_pattern"
canonical_chain_tags:
  - "subcircuit_expansion_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 9
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Subcircuit design pattern {#subcircuit-design-pattern}

## Encapsulation {#encapsulation}

Use `.subckt` / `.ends` to bundle reusable blocks; `inp_subcktexpand` rewrites internal nodes with hierarchical prefixes to avoid clashes ([Source: src/frontend/subckt.c#L50-L52]).

## Parameters {#parameters}

Pass geometry or corners through `.param` inside the subcircuit; `subckt_params_to_param` promotes them for numparam ([Source: ../15_parser_and_expansion/03_subcircuit_expansion_mechanics.md]).

## Pitfalls {#pitfalls}

- Avoid global node names inside reusable cells.
- Keep model names unique or rely on `modtranslate` to remap duplicates ([Source: src/frontend/subckt.c#L96-L97]).
