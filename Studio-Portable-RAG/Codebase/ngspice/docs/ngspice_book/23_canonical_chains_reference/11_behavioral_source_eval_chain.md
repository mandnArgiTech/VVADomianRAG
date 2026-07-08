---
title: "Behavioral source evaluation chain"
chapter: "23_canonical_chains_reference"
section: "11_behavioral_source_eval_chain"
section_number: "23.11"
topic: "behavioral_source_eval_chain"
mission_primary: "kernel_reimplementation"
mission_secondary: ["circuit_design_validation"]
related_files:
  - "src/spicelib/devices/asrc/asrcload.c"
  - "src/frontend/numparam/xpressn.c"
related_chapters:
  - "../09_source_devices/07_behavioral_source_b_element.md"
  - "../15_parser_and_expansion/05_expression_evaluator.md"
domain_concepts:
  - "behavioral_sources"
canonical_chain_tags:
  - "behavioral_source_eval_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 8
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Behavioral source evaluation chain {#behavioral-source-eval-chain}

## Summary {#summary}

Arbitrary sources (`ASRC`) contribute stamps through `ASRCload`, which walks each instance and evaluates the expression tree for function value and derivatives ([Source: src/spicelib/devices/asrc/asrcload.c#L19-L50]). Parameterized expressions in the deck are handled upstream by the numparam / expression machinery (`xpressn.c`).

## Stages {#stages}

`expression_eval` → `param_bind` → `device_load` ([Source: rag_index.json]).

## Canonical members {#members}

`src/spicelib/devices/asrc/asrcload.c`, `src/frontend/numparam/xpressn.c`

## Deep dives {#deep-dives}

- [B-element / behavioral sources](../09_source_devices/07_behavioral_source_b_element.md)
- [Expression evaluator](../15_parser_and_expansion/05_expression_evaluator.md)
