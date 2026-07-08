---
title: "Control block scripting"
chapter: "16_command_interpreter"
section: "05_control_block_scripting"
section_number: "16.5"
topic: "05_control_block_scripting"
mission_primary: "circuit_design_validation"
mission_secondary: []
related_files:
  - "src/frontend/inp.c"
related_chapters:
  - "../14_netlist_grammar/15_dot_control_block.md"
domain_concepts:
  - "control_scripting"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 10
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Control block scripting {#control-block-scripting}

## Extraction order {#extraction-order}

`inp_spsource` removes `.control` … `.endc` regions before the remaining deck is parsed as SPICE, storing commands for later execution ([Source: src/frontend/inp.c#L393-L460]).

## Pre-control vs post-control {#pre-control}

The parser distinguishes commands that must run **before** netlist elaboration (`pre_controls`) from those that should run with a compiled circuit (`controls`) ([Source: src/frontend/inp.c#L448-L460]).

## Typical script {#typical}

```text
.control
run
write results.raw
.endc
```

This pattern relies on `com_run`/`dosim` finishing before `write` serializes `plot_cur`.
