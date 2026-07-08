---
title: "Nutmeg / Spice3 command overview"
chapter: "16_command_interpreter"
section: "01_nutmeg_spice3_command_overview"
section_number: "16.1"
topic: "01_nutmeg_spice3_command_overview"
mission_primary: "circuit_design_validation"
mission_secondary: []
related_files:
  - "src/frontend/runcoms.c"
related_chapters:
  - "../14_netlist_grammar/15_dot_control_block.md"
domain_concepts:
  - "nutmeg_cli"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 10
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Nutmeg / Spice3 command overview {#nutmeg-spice3-command-overview}

## Simulation verbs {#simulation-verbs}

`runcoms.c` documents that `op`, `tran`, `ac`, `dc`, `listing`, `run`, `resume`, `stop`, and `trace` form the interactive simulation surface; immediate analyses call the shared `dosim` helper ([Source: src/frontend/runcoms.c#L36-L41], [Source: src/frontend/runcoms.c#L115-L175]).

## `dosim` responsibilities {#dosim}

`dosim` wraps analysis dispatch, optional raw-file capture, teardown, and `.measure` execution after successful runs ([Source: src/frontend/runcoms.c#L190-L361]).

## Circuit switching {#circuit-switching}

`com_scirc` selects `ft_curckt`, swaps completion keyword tables, and rebinds `modtab`/`dbs` for the active circuit ([Source: src/frontend/runcoms.c#L52-L112]).
