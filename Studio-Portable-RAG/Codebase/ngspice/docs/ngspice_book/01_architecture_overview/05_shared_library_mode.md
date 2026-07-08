---
title: "Shared library mode"
chapter: "01_architecture_overview"
section: "05_shared_library_mode"
section_number: "1.5"
topic: "05_shared_library_mode"
mission_primary: "circuit_design_validation"
mission_secondary: ["kernel_reimplementation"]
related_files:
  - "src/sharedspice.c"
related_chapters:
  - "../17_output_and_results/02_raw_file_format_spec.md"
  - "../16_command_interpreter/README.md"
domain_concepts: []
canonical_chain_tags:
  - "raw_output_consumption_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "ngspice core developer"
  - "advanced circuit designer"
estimated_reading_minutes: 10
last_updated_from_source_at: "2026-04-09T03:39:07.069653+00:00"
---

# Shared library mode {#shared-library-mode}

## Overview {#overview}

ngspice can be embedded as a shared library (`libngspice`). The implementation in `sharedspice.c` exposes C entry points such as `ngSpice_Init`, `ngSpice_Command`, `ngSpice_Circ`, and vector introspection helpers (`ngGet_Vec_Info`) so host applications can drive simulations without the standalone `ngspice` executable’s REPL ([Source: src/sharedspice.c#L515-L520, L693-L772]).

Initialization wires caller-supplied callbacks for printing, status, controlled exit, data streaming, and optional background-thread signaling ([Source: src/sharedspice.c#L518-L544]).

<!-- source: src/sharedspice.c -->

## What This Section Does {#what-it-does}

Anchors Mission-2 integrations (Python, MATLAB, custom GUIs) in the actual symbols exporters must call.

## `ngSpice_Init` Responsibilities {#ngspice-init}

`ngSpice_Init` records callbacks, seeds RNG helpers, initializes the front-end (`SIMinit`, `ft_cpinit`), sources `.spiceinit`, initializes graphics stubs (`DevInit`), and prints a banner identifying the shared build ([Source: src/sharedspice.c#L568-L667]).

## Feeding Netlists {#ngspice-circ}

`ngSpice_Circ` accepts a NULL-terminated array of strings; each line is copied and passed to `create_circbyline`, building the same internal deck representation as file-based input ([Source: src/sharedspice.c#L752-L768]).

## Command Execution {#ngspice-command}

`ngSpice_Command` runs an arbitrary nutmeg/ngspice command string via `runc` after verifying initialization ([Source: src/sharedspice.c#L696-L713]).

## Source Files {#source-files}

- **`src/sharedspice.c`** — shared library API surface.

## Related Chapters {#related-chapters}

- [Raw file format](../17_output_and_results/02_raw_file_format_spec.md) — consuming results from embedded runs.
- [Command interpreter](../16_command_interpreter/README.md) — syntax available via `ngSpice_Command`.

## Canonical Chains {#canonical-chains}

- `raw_output_consumption_chain` — host retrieves vectors through `ngGet_Vec_Info` or external raw files.
