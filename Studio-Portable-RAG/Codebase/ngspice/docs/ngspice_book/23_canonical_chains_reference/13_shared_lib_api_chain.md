---
title: "Shared library API chain"
chapter: "23_canonical_chains_reference"
section: "13_shared_lib_api_chain"
section_number: "23.13"
topic: "shared_lib_api_chain"
mission_primary: "circuit_design_validation"
mission_secondary: ["kernel_reimplementation"]
related_files:
  - "src/sharedspice.c"
  - "src/include/ngspice/sharedspice.h"
related_chapters:
  - "../01_architecture_overview/05_shared_library_mode.md"
domain_concepts:
  - "libngspice"
canonical_chain_tags:
  - "shared_lib_api_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 8
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Shared library API chain {#shared-lib-api-chain}

## Summary {#summary}

Embedders link against `libngspice` and drive the simulator through callbacks registered at init time. `ngSpice_Init` wires print/status/exit hooks before command dispatch ([Source: src/sharedspice.c#L518-L520]). Circuits are loaded with `ngSpice_Circ` and executed via `ngSpice_Command` ([Source: src/sharedspice.c#L696], [Source: src/sharedspice.c#L752]).

## Stages {#stages}

`shared_entry` → `vectors_export` ([Source: rag_index.json]).

## Canonical members {#members}

`src/sharedspice.c`, `src/include/ngspice/sharedspice.h`

## Deep dives {#deep-dives}

- [Shared library mode](../01_architecture_overview/05_shared_library_mode.md)
