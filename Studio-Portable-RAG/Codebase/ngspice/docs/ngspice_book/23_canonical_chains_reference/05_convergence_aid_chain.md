---
title: "Convergence aid chain"
chapter: "23_canonical_chains_reference"
section: "05_convergence_aid_chain"
section_number: "23.5"
topic: "convergence_aid_chain"
mission_primary: "kernel_reimplementation"
mission_secondary: ["circuit_design_validation"]
related_files:
  - "src/spicelib/analysis/dcop.c"
  - "src/spicelib/analysis/cktop.c"
  - "src/maths/ni/niiter.c"
related_chapters:
  - "../04_convergence_aids/01_convergence_aid_ladder.md"
domain_concepts:
  - "convergence_aids"
canonical_chain_tags:
  - "convergence_aid_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 8
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Convergence aid chain {#convergence-aid-chain}

## Summary {#summary}

When `NIiter` fails inside `CKTop`, ngspice escalates through GMIN stepping and source stepping (`dynamic_gmin`, `spice3_gmin`, `gillespie_src`, `spice3_src`, [Source: src/spicelib/analysis/cktop.c#L48-L72]).

## Stages {#stages}

`standard_nr` → `gmin_step` → `source_step` (`rag_index.json`).

## Deep dives {#deep-dives}

- [Convergence ladder](../04_convergence_aids/01_convergence_aid_ladder.md)
