---
title: "Vector manipulation commands"
chapter: "16_command_interpreter"
section: "03_vector_manipulation_commands"
section_number: "16.3"
topic: "03_vector_manipulation_commands"
mission_primary: "circuit_design_validation"
mission_secondary: []
related_files:
  - "src/frontend/com_display.c"
  - "src/frontend/com_let.c"
related_chapters:
  - "../17_output_and_results/01_vector_data_model.md"
domain_concepts:
  - "dvec_commands"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 9
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Vector manipulation commands {#vector-manipulation-commands}

## `display` {#display}

`com_display` lists vectors from the **current plot** unless specific names are supplied; the header reminds users to `setplot` when browsing history ([Source: src/frontend/com_display.c#L25-L30]).

## `let` and composition {#let}

`com_let` (see `com_let.c`) binds new vectors or scalar aliases for post-processing; it pairs with `com_display` for verification.

## Lookup model {#lookup}

Vectors hang off `struct plot` linked lists (`plot_list`) with hash-backed fast lookup (`pl_lookup_table`, [Source: src/include/ngspice/plot.h#L18-L22]).
