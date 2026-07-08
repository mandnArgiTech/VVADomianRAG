---
title: ".ac"
chapter: "14_netlist_grammar"
section: "05_dot_ac"
section_number: "14.5"
topic: "05_dot_ac"
mission_primary: "circuit_design_validation"
mission_secondary: ["kernel_reimplementation"]
related_files:
  - "src/spicelib/parser/inp2dot.c"
related_chapters:
  - "../03_analysis_drivers/04_ac_small_signal_acan.md"
domain_concepts:
  - "ac_analysis"
canonical_chain_tags:
  - "ac_analysis_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 8
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# .ac {#dot-ac}

## Syntax accepted by the parser {#syntax}

`dot_ac` documents the classic quadruplet: sweep type (`DEC`, `OCT`, `LIN`), number of points, start frequency, stop frequency ([Source: src/spicelib/parser/inp2dot.c#L186-L203]). Each field is pushed into the analysis instance via `INPapName`.

## Registration {#registration}

The `"AC"` job is created only if `ft_find_analysis("AC")` succeeds; otherwise the deck line errors out ([Source: src/spicelib/parser/inp2dot.c#L187-L192]).

## Dispatch {#dispatch}

`INP2dot` calls `dot_ac` when the first token is `.ac` ([Source: src/spicelib/parser/inp2dot.c#L678-L680]).
