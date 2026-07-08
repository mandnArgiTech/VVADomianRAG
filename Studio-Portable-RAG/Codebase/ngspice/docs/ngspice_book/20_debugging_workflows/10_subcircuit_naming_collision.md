---
title: "Subcircuit naming collision"
chapter: "20_debugging_workflows"
section: "10_subcircuit_naming_collision"
section_number: "20.10"
topic: "10_subcircuit_naming_collision"
mission_primary: "circuit_design_validation"
mission_secondary: []
related_files:
  - "src/frontend/subckt.c"
related_chapters:
  - "../15_parser_and_expansion/03_subcircuit_expansion_mechanics.md"
domain_concepts:
  - "subckt_collisions"
canonical_chain_tags:
  - "subcircuit_expansion_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 9
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Subcircuit naming collision {#subcircuit-naming-collision}

## Hierarchical prefixes {#prefixes}

`inp_subcktexpand` rewrites internal nodes by appending `subcktname:` prefixes, stacking for nested hierarchies ([Source: src/frontend/subckt.c#L50-L52]).

## When collisions still happen {#when}

Duplicate **global** net names outside subcircuits, or reusing the same instance label twice, still short-circuit the hierarchy protections.

## Model collisions {#model-collisions}

`devmodtranslate` must remap `.model` references when identically named models appear in sibling scopes ([Source: src/frontend/subckt.c#L96-L97]).

## Fix {#fix}

Rename instances/models uniquely and verify flattened listings via `listing` commands or preprocessor dumps.
