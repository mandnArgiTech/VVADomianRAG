---
title: ".measure extraction chain"
chapter: "23_canonical_chains_reference"
section: "09_measure_extraction_chain"
section_number: "23.9"
topic: "measure_extraction_chain"
mission_primary: "circuit_design_validation"
mission_secondary: []
related_files:
  - "src/frontend/measure.c"
  - "src/frontend/com_measure2.c"
related_chapters:
  - "../14_netlist_grammar/14_dot_measure.md"
  - "../17_output_and_results/04_measure_extraction_idioms.md"
domain_concepts:
  - "post_simulation_measure"
canonical_chain_tags:
  - "measure_extraction_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 8
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# .measure extraction chain {#measure-extraction-chain}

## Summary {#summary}

After a successful analysis, `dosim` invokes `do_measure` when the deck registered measurements and a last analysis exists ([Source: src/frontend/runcoms.c#L359-L361]). The measure subsystem documents its own entry: evaluation runs after simulation from `dosim`, and `com_meas` serves interactive `meas` ([Source: src/frontend/measure.c#L1-L6]).

## Stages {#stages}

`sim_complete` → `measure_parse` → `vector_walk` ([Source: rag_index.json]).

## Canonical members {#members}

`src/frontend/measure.c`, `src/frontend/com_measure2.c`

## Deep dives {#deep-dives}

- [.measure grammar](../14_netlist_grammar/14_dot_measure.md)
- [Measure idioms](../17_output_and_results/04_measure_extraction_idioms.md)
