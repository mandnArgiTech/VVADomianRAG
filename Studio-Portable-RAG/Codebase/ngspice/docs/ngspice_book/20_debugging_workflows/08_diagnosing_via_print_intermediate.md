---
title: "Diagnosing via print and intermediate dumps"
chapter: "20_debugging_workflows"
section: "08_diagnosing_via_print_intermediate"
section_number: "20.8"
topic: "08_diagnosing_via_print_intermediate"
mission_primary: "circuit_design_validation"
mission_secondary: []
related_files:
  - "src/frontend/com_display.c"
  - "src/frontend/dotcards.c"
related_chapters:
  - "../16_command_interpreter/03_vector_manipulation_commands.md"
domain_concepts:
  - "interactive_debug"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 9
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Diagnosing via print and intermediate dumps {#diagnosing-via-print-intermediate}

## Vector introspection {#vector-introspection}

`com_display` lists vectors for the active plot; use `setplot` to hop between OP, TRAN, and AC results ([Source: src/frontend/com_display.c#L25-L30]).

## OP dumps {#op-dumps}

`ft_cktcoms` prints node voltages and source currents after `.op` when not in terse/raw-only mode ([Source: src/frontend/dotcards.c#L221-L251]).

## Break + inspect {#break}

Combine `stop when` breakpoints (`breakp.c`) with `print` to snapshot state mid-transient ([Source: src/frontend/breakp.c#L29-L37]).
