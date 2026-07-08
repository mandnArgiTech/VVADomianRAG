---
title: "Netlist to simulation chain"
chapter: "23_canonical_chains_reference"
section: "07_netlist_to_simulation_chain"
section_number: "23.7"
topic: "netlist_to_simulation_chain"
mission_primary: "circuit_design_validation"
mission_secondary: ["kernel_reimplementation"]
related_files:
  - "src/frontend/inp.c"
  - "src/spicelib/parser/inpdomod.c"
  - "src/frontend/dotcards.c"
  - "src/frontend/subckt.c"
  - "src/frontend/numparam/xpressn.c"
  - "src/spicelib/devices/cktinit.c"
related_chapters:
  - "../14_netlist_grammar/01_netlist_overall_structure.md"
  - "../15_parser_and_expansion/01_netlist_tokenization.md"
  - "../15_parser_and_expansion/02_dotcommand_dispatch.md"
  - "../15_parser_and_expansion/03_subcircuit_expansion_mechanics.md"
domain_concepts:
  - "netlist_parsing"
canonical_chain_tags:
  - "netlist_to_simulation_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
  - "advanced circuit designer"
estimated_reading_minutes: 10
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Netlist to simulation chain {#netlist-to-simulation-chain}

## Summary {#summary}

User-facing path from a deck on disk through frontend parsing, model binding, subcircuit expansion, parameter expression evaluation, circuit initialization, and finally analysis execution. The deck reader `inp_spsource` hands completed decks to `inp_dodeck` ([Source: src/frontend/inp.c#L300-L320], [Source: src/frontend/inp.c#L752-L770]). Dot-command lines (`.save`, `.meas`, etc.) are collected into `ci_commands` before execution-time helpers such as `ft_dotsaves` consume them ([Source: src/frontend/dotcards.c#L50-L54]).

## Stages {#stages}

`tokenize` → `dispatch_devices_dotcmds` → `subckt_expand` → `param_substitute` → `ckt_init` → `analysis_run` ([Source: rag_index.json canonical_chains entry `netlist_to_simulation_chain`]).

## Canonical members {#members}

- `src/frontend/inp.c`, `src/spicelib/parser/inpdomod.c`, `src/frontend/dotcards.c`, `src/frontend/subckt.c`, `src/frontend/numparam/xpressn.c`, `src/spicelib/devices/cktinit.c`

## Deep dives {#deep-dives}

- [Netlist structure](../14_netlist_grammar/01_netlist_overall_structure.md)
- [Tokenization](../15_parser_and_expansion/01_netlist_tokenization.md)
- [Dot dispatch](../15_parser_and_expansion/02_dotcommand_dispatch.md)
- [Subcircuit expansion](../15_parser_and_expansion/03_subcircuit_expansion_mechanics.md)
