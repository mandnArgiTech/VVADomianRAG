---
title: "Netlist overall structure"
chapter: "14_netlist_grammar"
section: "01_netlist_overall_structure"
section_number: "14.1"
topic: "01_netlist_overall_structure"
mission_primary: "circuit_design_validation"
mission_secondary: ["kernel_reimplementation"]
related_files:
  - "src/frontend/inp.c"
  - "src/spicelib/parser/inp2dot.c"
related_chapters:
  - "../15_parser_and_expansion/01_netlist_tokenization.md"
  - "../23_canonical_chains_reference/07_netlist_to_simulation_chain.md"
domain_concepts:
  - "netlist_structure"
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

# Netlist overall structure {#netlist-overall-structure}

## Deck, title, and execution split {#deck-title}

`inp_spsource` reads the deck, filters certain dot lines into a post-run command list, and calls `inp_dodeck` to bind the circuit into `ft_curckt` ([Source: src/frontend/inp.c#L295-L320], [Source: src/frontend/inp.c#L752-L764]). The first line is traditionally a **title**; remaining lines mix **element cards** (devices) and **control cards** (dot directives).

## Where dot cards become analyses {#dot-to-analysis}

During circuit elaboration the parser dispatches lines beginning with `.` through `INP2dot`, which branches on the first token and constructs analysis jobs (`OP`, `DC`, `TRAN`, …) via `ft_find_analysis` + `newAnalysis` ([Source: src/spicelib/parser/inp2dot.c#L631-L692]).

## Frontend-only dot lines {#frontend-dot}

Some directives never become `JOB` records: `inp_spsource` explicitly pulls `.save`, `.width`, `.four`, `.print`, `.plot`, `.meas`, `.tf`, and related Spice-2 compatibility cards into `wl_first` for `ft_cktcoms` / measure handling later ([Source: src/frontend/inp.c#L295-L297], [Source: src/frontend/dotcards.c#L50-L54]).

## Practical authoring rules {#rules}

- Keep **one analysis directive** per simulation intent; extras queue as additional tasks on the same `CKTcircuit`.
- Place `.options` near the top so tolerances affect every downstream analysis ([Source: src/spicelib/parser/inp2dot.c#L723-L727]).
