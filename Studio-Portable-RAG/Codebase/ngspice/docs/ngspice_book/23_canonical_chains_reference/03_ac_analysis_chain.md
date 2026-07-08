---
title: "AC analysis chain"
chapter: "23_canonical_chains_reference"
section: "03_ac_analysis_chain"
section_number: "23.3"
topic: "ac_analysis_chain"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/spicelib/analysis/acan.c"
  - "src/spicelib/analysis/cktload.c"
related_chapters:
  - "../03_analysis_drivers/04_ac_small_signal_acan.md"
domain_concepts:
  - "ac_small_signal_analysis"
canonical_chain_tags:
  - "ac_analysis_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 7
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# AC analysis chain {#ac-analysis-chain}

## Summary {#summary}

DC operating point (or linearization point) followed by frequency sweeps that rebuild the complex Jacobian through `DEVacLoad` inside the AC driver ([Source: ../03_analysis_drivers/04_ac_small_signal_acan.md]).

## Stages {#stages}

`dc_op_first` → `linearization` → `complex_solve_per_frequency` (`rag_index.json`).

## Canonical members {#members}

`src/spicelib/analysis/acan.c`, `src/spicelib/analysis/cktload.c`

## Deep dives {#deep-dives}

- [ACan](../03_analysis_drivers/04_ac_small_signal_acan.md)
