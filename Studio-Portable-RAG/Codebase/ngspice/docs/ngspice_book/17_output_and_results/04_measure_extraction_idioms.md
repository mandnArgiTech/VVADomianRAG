---
title: "Measure extraction idioms"
chapter: "17_output_and_results"
section: "04_measure_extraction_idioms"
section_number: "17.4"
topic: "04_measure_extraction_idioms"
mission_primary: "circuit_design_validation"
mission_secondary: []
related_files:
  - "src/frontend/measure.c"
  - "src/frontend/runcoms.c"
related_chapters:
  - "../14_netlist_grammar/14_dot_measure.md"
domain_concepts:
  - "measure_idioms"
canonical_chain_tags:
  - "measure_extraction_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 10
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Measure extraction idioms {#measure-extraction-idioms}

## When `.measure` runs {#when}

`dosim` triggers `do_measure` only after a successful analysis and when `ci_meas` data exists ([Source: src/frontend/runcoms.c#L359-L361]).

## Interactive parity {#interactive}

`com_meas` reuses the same tokenizer/evaluator as deck `.measure`, enabling scripted regression checks inside `.control` ([Source: src/frontend/measure.c#L30-L34]).

## Vector dependencies {#vector-dependencies}

`ft_savemeasure` pre-scans `.measure` lines so referenced traces are not garbage-collected ([Source: src/frontend/dotcards.c#L166-L179]).
