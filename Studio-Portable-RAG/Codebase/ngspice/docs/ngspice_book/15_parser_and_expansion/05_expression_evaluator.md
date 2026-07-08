---
title: "Expression evaluator"
chapter: "15_parser_and_expansion"
section: "05_expression_evaluator"
section_number: "15.5"
topic: "05_expression_evaluator"
mission_primary: "circuit_design_validation"
mission_secondary: ["kernel_reimplementation"]
related_files:
  - "src/spicelib/devices/asrc/asrcload.c"
  - "src/frontend/numparam/xpressn.c"
related_chapters:
  - "../09_source_devices/07_behavioral_source_b_element.md"
domain_concepts:
  - "expression_trees"
canonical_chain_tags:
  - "behavioral_source_eval_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 10
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Expression evaluator {#expression-evaluator}

## Device-side evaluation {#device-side}

`ASRCload` evaluates each instance’s function tree for value and derivatives before stamping the MNA matrix ([Source: src/spicelib/devices/asrc/asrcload.c#L47-L50]).

## Frontend algebra {#frontend-algebra}

Deck-level expressions (`xpressn.c`) handle parameter algebra, complements, and substitutions that occur **before** devices exist; bridging the two layers is why numparam signals (`nupa_signal`) exist ([Source: src/frontend/numparam/numpaif.h#L16]).

## Debugging {#debugging}

When `B` sources misbehave, verify both the **flattened netlist** (post numparam) and the **ASRC tree** evaluation order—mismatches often show up as derivative NaNs in Newton.
