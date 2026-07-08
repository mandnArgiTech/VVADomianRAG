---
title: "Breakpoints and alter"
chapter: "16_command_interpreter"
section: "06_breakpoints_and_alter"
section_number: "16.6"
topic: "06_breakpoints_and_alter"
mission_primary: "circuit_design_validation"
mission_secondary: []
related_files:
  - "src/frontend/breakp.c"
related_chapters:
  - "../20_debugging_workflows/08_diagnosing_via_print_intermediate.md"
domain_concepts:
  - "breakpoints"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 9
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Breakpoints and alter {#breakpoints-and-alter}

## `stop` command {#stop}

`breakp.c` documents `stop after N` and `stop when var cond val`; multiple clauses on one line form a conjunction ([Source: src/frontend/breakp.c#L29-L34], [Source: src/frontend/breakp.c#L36-L37]).

## Data structures {#data-structures}

Each clause allocates a `dbcomm` record chained through `db_also`, which `runcoms.c` later consults via the per-circuit `dbs` pointer when switching circuits ([Source: src/frontend/runcoms.c#L110-L111]).

## `alter` {#alter}

Device parameter tweaks (`alter`) are implemented in `breakp2.c` / spice interface helpers—use them to mimic process skew without re-parsing the deck.
