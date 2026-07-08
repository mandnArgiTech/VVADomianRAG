---
title: ".measure"
chapter: "14_netlist_grammar"
section: "14_dot_measure"
section_number: "14.14"
topic: "14_dot_measure"
mission_primary: "circuit_design_validation"
mission_secondary: []
related_files:
  - "src/spicelib/parser/inp2dot.c"
  - "src/frontend/measure.c"
  - "src/frontend/runcoms.c"
related_chapters:
  - "../17_output_and_results/04_measure_extraction_idioms.md"
  - "../23_canonical_chains_reference/09_measure_extraction_chain.md"
domain_concepts:
  - "measure_directive"
canonical_chain_tags:
  - "measure_extraction_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 10
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# .measure {#dot-measure}

## Parser pass {#parser-pass}

`INP2dot` ignores `.measure`/`.meas` tokens so they do not instantiate analyses; they are consumed later ([Source: src/spicelib/parser/inp2dot.c#L735-L738]).

## Runtime hook {#runtime}

`measure.c` documents that `do_measure()` runs from `dosim()` after simulation completes ([Source: src/frontend/measure.c#L1-L3]). `runcoms.c` calls `do_measure` when measurements exist and the last analysis pointer is valid ([Source: src/frontend/runcoms.c#L359-L361]).

## Variable pre-scan {#prescan}

`ft_savemeasure` walks stored `.measure` lines and invokes `measure_extract_variables` so dependent vectors are retained ([Source: src/frontend/dotcards.c#L166-L179]).

## Idioms {#idioms}

Worked examples and pitfalls appear in [chapter 17 §4](../17_output_and_results/04_measure_extraction_idioms.md).
