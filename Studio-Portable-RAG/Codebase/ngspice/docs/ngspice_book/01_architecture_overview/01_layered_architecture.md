---
title: "Layered architecture"
chapter: "01_architecture_overview"
section: "01_layered_architecture"
section_number: "1.1"
topic: "01_layered_architecture"
mission_primary: "kernel_reimplementation"
mission_secondary: ["circuit_design_validation"]
related_files:
  - "src/frontend/inp.c"
  - "src/spicelib/analysis/cktload.c"
  - "src/include/ngspice/cktdefs.h"
related_chapters:
  - "../01_architecture_overview/06_directory_structure_walkthrough.md"
  - "../02_numerical_kernel_core/01_circuit_load_dispatch_cktload.md"
domain_concepts:
  - "mna_modified_nodal_analysis"
canonical_chain_tags:
  - "netlist_to_simulation_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
  - "ngspice core developer"
estimated_reading_minutes: 10
last_updated_from_source_at: "2026-04-09T03:39:07.072860+00:00"
---

# Layered architecture {#layered-architecture}

## Overview {#overview}

ngspice splits responsibilities into recognizable layers:

1. **Frontend (Spice3 / nutmeg)** — Parses netlists, expands subcircuits, manages interactive commands, and bridges user I/O. `inp.c` is the central compilation unit for “dealing with spice input decks and command scripts” ([Source: src/frontend/inp.c#L6-L9]).
2. **Spicelib analysis + circuit core** — Owns `CKTcircuit`, schedules analyses, and calls `CKTload` each Newton iteration ([Source: src/spicelib/analysis/cktload.c#L9-L13]).
3. **Device layer** — Implements `SPICEdev` tables (`DEVload`, `DEVacLoad`, …) registered in `DEVices[]` (see [SPICEdev contract](03_spicedev_plugin_contract.md)).
4. **Maths** — Sparse matrix (`SMP*`) and numerical iteration (`NI*`).

This separation keeps parsing concerns out of the Jacobian stamping path and allows the same kernel to run stand-alone, batch, or embedded.

<!-- source: src/frontend/inp.c -->
<!-- source: src/spicelib/analysis/cktload.c -->

## What This Section Does {#what-it-does}

It names the boundaries agents should respect when tracing behavior: a convergence bug might originate in `NIiter`, in a specific `DEVload`, or in netlist expansion—but rarely all three at once.

## Control Flow Snapshot {#control-flow}

At a high level, a batch run moves from text lines (`inp.c` helpers) to a populated `CKTcircuit`, then into analysis drivers (Chapter 3) that loop: **load → factor/solve → test**. `CKTload` is the fan-in point from analysis back to all devices ([Source: src/spicelib/analysis/cktload.c#L61-L75]).

## Source Files {#source-files}

- **`src/frontend/inp.c`** — Netlist / script front door.
- **`src/spicelib/analysis/cktload.c`** — Kernel dispatch to `DEVload`.
- **`src/include/ngspice/cktdefs.h`** — Shared `CKTcircuit` definition.

## Related Chapters {#related-chapters}

- [Directory walkthrough](06_directory_structure_walkthrough.md)
- [CKTload dispatch](../02_numerical_kernel_core/01_circuit_load_dispatch_cktload.md)
- [Netlist grammar](../14_netlist_grammar/README.md) — user-visible side of the frontend.

## Canonical Chains {#canonical-chains}

- `netlist_to_simulation_chain` — parser → circuit → run (see `rag_index.json`).
