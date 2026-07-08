---
title: "Netlist tokenization"
chapter: "15_parser_and_expansion"
section: "01_netlist_tokenization"
section_number: "15.1"
topic: "01_netlist_tokenization"
mission_primary: "circuit_design_validation"
mission_secondary: []
related_files:
  - "src/frontend/inpcom.c"
  - "src/spicelib/parser/inp2dot.c"
related_chapters:
  - "../14_netlist_grammar/01_netlist_overall_structure.md"
domain_concepts:
  - "deck_tokenization"
canonical_chain_tags:
  - "netlist_to_simulation_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 10
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Netlist tokenization {#netlist-tokenization}

## `inp_readall` pipeline {#inp-readall}

`inp_readall` is the central deck ingestor: it calls `inp_read`, then (for non-command files) normalizes whitespace, prepares numparam hooks, and performs subcircuit parameter promotion before the deck reaches `INP2*` parsers ([Source: src/frontend/inpcom.c#L6-L10], [Source: src/frontend/inpcom.c#L485-L517]).

## Continuations and includes {#continuations}

The header documents continuation-line merging, library inclusion, and debug printouts—behavior implemented in the body of `inp_readall` / helpers ([Source: src/frontend/inpcom.c#L478-L483]).

## Parser-facing tokens {#parser-facing}

Downstream, `INPgetTok` family routines chew the `card->line` buffer; `INP2dot` demonstrates first-token dispatch on dot cards ([Source: src/spicelib/parser/inp2dot.c#L642-L660]).
