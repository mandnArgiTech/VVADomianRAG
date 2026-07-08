---
title: "Print format (text output)"
chapter: "17_output_and_results"
section: "03_print_format_text_output"
section_number: "17.3"
topic: "03_print_format_text_output"
mission_primary: "circuit_design_validation"
mission_secondary: []
related_files:
  - "src/frontend/dotcards.c"
related_chapters:
  - "../16_command_interpreter/04_plot_print_commands.md"
domain_concepts:
  - "text_print"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 9
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Print format (text output) {#print-format-text-output}

## Deck-level `.print` {#deck-print}

Legacy `.print` lines are filtered out during `INP2dot`, so modern decks should use interactive `print` after `run` ([Source: src/spicelib/parser/inp2dot.c#L647-L651]).

## Post-run listings {#post-run}

`ft_cktcoms` still honors Spice-2 compatibility by iterating `ci_commands` and dispatching `com_print` when transfer-function plots are present ([Source: src/frontend/dotcards.c#L260-L269]).

## Formatting knobs {#formatting}

`printnum` helpers (used when dumping OP results) respect global precision variables set via `option`/`set` ([Source: src/frontend/dotcards.c#L199-L241]).
