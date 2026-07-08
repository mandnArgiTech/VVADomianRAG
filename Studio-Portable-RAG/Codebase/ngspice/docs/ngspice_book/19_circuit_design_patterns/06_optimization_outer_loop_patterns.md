---
title: "Optimization outer-loop patterns"
chapter: "19_circuit_design_patterns"
section: "06_optimization_outer_loop_patterns"
section_number: "19.6"
topic: "06_optimization_outer_loop_patterns"
mission_primary: "circuit_design_validation"
mission_secondary: []
related_files:
  - "src/sharedspice.c"
related_chapters:
  - "../01_architecture_overview/05_shared_library_mode.md"
domain_concepts:
  - "optimization_wrapper"
canonical_chain_tags:
  - "shared_lib_api_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 9
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Optimization outer-loop patterns {#optimization-outer-loop-patterns}

## Why outer loops {#why}

`ngspice` solves equations, not objective functions; gradient-free or model-based optimizers belong in the host process ([Source: src/sharedspice.c#L518-L520], [Source: src/sharedspice.c#L696-L713]).

## Shared-library recipe {#recipe}

1. `ngSpice_Init` with callbacks.
2. For each candidate, `ngSpice_Circ` reloads the deck text.
3. `ngSpice_Command("run")` executes analyses.
4. Pull vectors via exported accessors and compute cost.

## `.measure` shortcut {#measure-shortcut}

Encode figures-of-merit in `.measure` so the outer loop reads scalars instead of full waveforms ([Source: src/frontend/measure.c#L1-L3]).
