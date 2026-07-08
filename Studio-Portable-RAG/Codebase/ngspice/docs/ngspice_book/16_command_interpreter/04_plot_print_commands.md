---
title: "Plot and print commands"
chapter: "16_command_interpreter"
section: "04_plot_print_commands"
section_number: "16.4"
topic: "04_plot_print_commands"
mission_primary: "circuit_design_validation"
mission_secondary: []
related_files:
  - "src/frontend/com_plot.c"
related_chapters:
  - "../17_output_and_results/03_print_format_text_output.md"
domain_concepts:
  - "plotit"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 8
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Plot and print commands {#plot-print-commands}

## `plot` {#plot}

`com_plot` forwards its `wordlist` to `plotit`, which handles axis limits, `vs` sweeps, and GUI backends ([Source: src/frontend/com_plot.c#L11-L16]).

## `print` {#print}

Textual tabulation routes through `com_print` (declared via nutmeg headers) and shares vector resolution with `display`.

## Batch note {#batch}

In `--batch` mode, prefer `wrdata`/`write`/`raw` paths documented in [chapter 17](../17_output_and_results/README.md) because interactive plotting may be unavailable.
