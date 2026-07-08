---
title: "Pole-zero (PZan)"
chapter: "03_analysis_drivers"
section: "09_pole_zero_pzan"
section_number: "3.9"
topic: "09_pole_zero_pzan"
mission_primary: "kernel_reimplementation"
mission_secondary: ["circuit_design_validation"]
related_files:
  - "src/spicelib/analysis/pzan.c"
related_chapters:
  - "../14_netlist_grammar/08_dot_tf_dot_sens_dot_pz.md"
domain_concepts:
  - "pz_pole_zero_eigensystem"
canonical_chain_tags: []
numerical_invariants_introduced:
  - "pz_pole_zero_eigensystem"
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 9
last_updated_from_source_at: "2026-04-09T03:39:07.072860+00:00"
---

# Pole-zero (PZan) {#pole-zero-pzan}

## Overview {#overview}

`PZan` initializes pole-zero data (`PZinit`), solves the DC operating point via `CKTop`, switches to small-signal mode (`MODEINITSMSIG`), and calls `CKTload` to ensure linearized parameters are current before running the pole-zero kernel ([Source: src/spicelib/analysis/pzan.c#L29-L43]).

Optional debugging may dump the linearization as a real plot when `CKTkeepOpInfo` is set ([Source: src/spicelib/analysis/pzan.c#L45-L55]).

<!-- source: src/spicelib/analysis/pzan.c -->

## Source Files {#source-files}

- **`src/spicelib/analysis/pzan.c`**
- Supporting eigensolvers live under `src/maths/ni/` (e.g., `nipzmeth.c` per `rag_index.json`).

## Related Chapters {#related-chapters}

- [.pz grammar](../14_netlist_grammar/08_dot_tf_dot_sens_dot_pz.md)
