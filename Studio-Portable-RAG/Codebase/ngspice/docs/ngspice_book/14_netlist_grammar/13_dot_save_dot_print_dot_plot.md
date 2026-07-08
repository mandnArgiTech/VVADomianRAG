---
title: ".save .print .plot"
chapter: "14_netlist_grammar"
section: "13_dot_save_dot_print_dot_plot"
section_number: "14.13"
topic: "13_dot_save_dot_print_dot_plot"
mission_primary: "circuit_design_validation"
mission_secondary: []
related_files:
  - "src/frontend/dotcards.c"
  - "src/spicelib/parser/inp2dot.c"
related_chapters:
  - "../17_output_and_results/README.md"
  - "../16_command_interpreter/04_plot_print_commands.md"
domain_concepts:
  - "output_directives"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 9
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# .save .print .plot {#dot-save-dot-print-dot-plot}

## Legacy dot cards in `INP2dot` {#legacy-inp2dot}

The netlist parser warns that `.print`, `.plot`, and `.width` are obsolete and ignores them during `INP2dot` ([Source: src/spicelib/parser/inp2dot.c#L647-L651]).

## Frontend command lists {#frontend}

`inp_spsource` strips `.save`, `.print`, `.plot`, `.width`, `.four`, `.op`, `.meas`, `.tf`, etc., into `wl_first` so they can execute after parsing via `ft_dotsaves` / `ft_cktcoms` ([Source: src/frontend/inp.c#L295-L297], [Source: src/frontend/dotcards.c#L50-L54]).

## `.save` execution {#save}

`ft_dotsaves` walks `ci_commands`, collects `.save` lines, tokenizes the remainder, and calls `com_save` ([Source: src/frontend/dotcards.c#L56-L75]).

## Interactive replacements {#interactive}

Prefer nutmeg `plot`, `print`, and `write` commands ([chapter 16](../16_command_interpreter/README.md)) for modern workflows; they operate on `dvec` results after simulation.
