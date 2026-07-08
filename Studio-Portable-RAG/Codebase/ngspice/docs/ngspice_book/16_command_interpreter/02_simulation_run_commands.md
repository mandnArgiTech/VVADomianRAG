---
title: "Simulation run commands"
chapter: "16_command_interpreter"
section: "02_simulation_run_commands"
section_number: "16.2"
topic: "02_simulation_run_commands"
mission_primary: "circuit_design_validation"
mission_secondary: []
related_files:
  - "src/frontend/runcoms.c"
related_chapters:
  - "../03_analysis_drivers/README.md"
domain_concepts:
  - "run_tran_ac_dc"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 9
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Simulation run commands {#simulation-run-commands}

## Thin wrappers {#wrappers}

`com_op`, `com_dc`, `com_ac`, `com_tran`, `com_tf`, `com_sens`, `com_disto`, `com_noise`, and `com_pz` each call `dosim` with a string token naming the analysis ([Source: src/frontend/runcoms.c#L115-L175]).

## `run` vs explicit analyses {#run}

`com_run` simply invokes `dosim("run", wl)` so deck-scheduled jobs execute in batch order ([Source: src/frontend/runcoms.c#L369-L374]).

## Raw file handling {#raw}

Globals `rawfileFp`, `rawfileBinary`, and `last_used_rawfile` (declared in `runcoms.c`) coordinate writing plots during `dosim` ([Source: src/frontend/runcoms.c#L44-L49]).
