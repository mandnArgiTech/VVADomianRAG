---
title: ".control block"
chapter: "14_netlist_grammar"
section: "15_dot_control_block"
section_number: "14.15"
topic: "15_dot_control_block"
mission_primary: "circuit_design_validation"
mission_secondary: []
related_files:
  - "src/frontend/inp.c"
related_chapters:
  - "../16_command_interpreter/05_control_block_scripting.md"
domain_concepts:
  - "control_block"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 10
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# .control block {#dot-control-block}

## Separation from the analog deck {#separation}

`inp_spsource` walks the deck twice: it first extracts `.control` … `.endc` regions into `controls` / `pre_controls` wordlists, optionally executes pre-control commands, then continues parsing the remaining SPICE cards ([Source: src/frontend/inp.c#L348-L516]).

## Redundant cards {#redundant}

Multiple `.control` statements are tolerated but warned as redundant ([Source: src/frontend/inp.c#L429-L433]).

## Execution model {#execution}

Control lines are fed through the nutmeg command processor (`cp_*` APIs), enabling scripting (`run`, `plot`, `meas`, etc.) around the compiled circuit.

## Further reading {#further-reading}

See [chapter 16 §5](../16_command_interpreter/05_control_block_scripting.md) for practical patterns.
