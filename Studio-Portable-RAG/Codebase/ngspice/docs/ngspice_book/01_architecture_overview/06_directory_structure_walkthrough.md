---
title: "Directory structure walkthrough"
chapter: "01_architecture_overview"
section: "06_directory_structure_walkthrough"
section_number: "1.6"
topic: "06_directory_structure_walkthrough"
mission_primary: "kernel_reimplementation"
mission_secondary: ["circuit_design_validation"]
related_files: []
related_chapters:
  - "../_meta/path_registry.md"
  - "01_layered_architecture.md"
domain_concepts: []
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 8
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Directory structure walkthrough {#directory-structure-walkthrough}

## Overview {#overview}

The ngspice tree groups code by responsibility. Paths drifted from classic SPICE3 layouts; the book maintains a human-edited registry so citations stay accurate—see [`_meta/path_registry.md`](../_meta/path_registry.md).

## Frontend {#frontend}

- **`src/frontend/`** — Netlist ingestion (`inp.c`), dot-card handling (`dotcards.c`), interactive command processor, plotting hooks, and numparam integration. Start here for Mission-2 tracing.

## Spicelib {#spicelib}

- **`src/spicelib/analysis/`** — Analysis drivers (`dcop.c`, `dctran.c`, `cktload.c`, …) and shared circuit operations.
- **`src/spicelib/parser/`** — Model and instance parsing helpers.
- **`src/spicelib/devices/`** — `dev.c` (device registration), `cktinit.c`, and per-device subfolders (`mos9/`, `bsim4/`, …).

## Maths {#maths}

- **`src/maths/ni/`** — Newton iteration (`niiter.c`), convergence (`niconv.c`), integration (`niinteg.c`), pole-zero helpers, etc.
- **`src/maths/sparse/`** — Default sparse LU solver used by `SMP*` wrappers.

## Includes {#includes}

- **`src/include/ngspice/`** — Public headers such as `cktdefs.h`, `devdefs.h`, `smpdefs.h`. Always prefer these paths in citations.

## Shared / Misc {#shared}

- **`src/sharedspice.c`** — Embeddable API (`ngSpice_*`).
- **`src/misc/`** — Cross-cutting utilities (diagnostics, time, …).

## Related Chapters {#related-chapters}

- [Layered architecture](01_layered_architecture.md)
- [Path registry](../_meta/path_registry.md)

## Source Files {#source-files}

- No single file; use registry + repository tree.
