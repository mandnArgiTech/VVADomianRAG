---
title: "Transient step chain"
chapter: "23_canonical_chains_reference"
section: "02_transient_step_chain"
section_number: "23.2"
topic: "transient_step_chain"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/spicelib/analysis/dctran.c"
  - "src/maths/ni/niiter.c"
  - "src/maths/ni/niinteg.c"
  - "src/spicelib/devices/cktaccept.c"
  - "src/spicelib/analysis/ckttrunc.c"
related_chapters:
  - "../03_analysis_drivers/03_transient_dctran.md"
  - "../05_numerical_integration/06_timestep_control_law.md"
domain_concepts:
  - "transient_analysis"
canonical_chain_tags:
  - "transient_step_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 9
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Transient step chain {#transient-step-chain}

## Summary {#summary}

One accepted transient timepoint: predictor/integration → `NIiter` → `CKTtrunc` LTE merge → optional order promotion; failures roll back `CKTdelta` ([Source: src/spicelib/analysis/dctran.c#L730-L873]).

## Stages {#stages}

`predictor` → `device_load_with_charge` → `nr_iteration` → `lte_estimation` → `step_accept_or_reject` (`rag_index.json`).

## Canonical members {#members}

`src/spicelib/analysis/dctran.c`, `src/maths/ni/niiter.c`, `src/maths/ni/niinteg.c`, `src/spicelib/devices/cktaccept.c`, `src/spicelib/analysis/ckttrunc.c`

## Deep dives {#deep-dives}

- [DCtran](../03_analysis_drivers/03_transient_dctran.md)
- [Timestep control](../05_numerical_integration/06_timestep_control_law.md)
