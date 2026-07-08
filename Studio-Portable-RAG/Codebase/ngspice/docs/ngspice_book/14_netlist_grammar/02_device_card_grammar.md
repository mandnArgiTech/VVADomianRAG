---
title: "Device card grammar"
chapter: "14_netlist_grammar"
section: "02_device_card_grammar"
section_number: "14.2"
topic: "02_device_card_grammar"
mission_primary: "circuit_design_validation"
mission_secondary: ["kernel_reimplementation"]
related_files:
  - "src/spicelib/parser/inp2r.c"
  - "src/spicelib/parser/inpdomod.c"
related_chapters:
  - "../07_device_model_contract/01_spicedev_struct_anatomy.md"
  - "../15_parser_and_expansion/01_netlist_tokenization.md"
domain_concepts:
  - "device_instances"
canonical_chain_tags:
  - "device_load_dispatch_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 9
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Device card grammar {#device-card-grammar}

## Letter-driven parsers {#letter-driven}

Each leading SPICE letter (`R`, `C`, `M`, …) maps to a dedicated `INP2*` routine. Resistors illustrate the pattern: comment block documents the accepted tokens, then `INP2R` parses nodes, value, optional model, and geometry keywords ([Source: src/spicelib/parser/inp2r.c#L20-L44]).

## Models vs values {#models}

Model cards (`.model`) are collected in an earlier pass (`inpdomod.c`) so instance lines can resolve `mname` handles before `INP2*` functions allocate `GENinstance` records ([Source: ../15_parser_and_expansion/04_parameter_substitution_numparam.md]).

## Kernel touchpoint {#kernel}

Parsed instances ultimately hang off `ckt->CKThead[type]` lists consumed by `CKTload` ([Source: src/spicelib/analysis/cktload.c#L61-L64]).
