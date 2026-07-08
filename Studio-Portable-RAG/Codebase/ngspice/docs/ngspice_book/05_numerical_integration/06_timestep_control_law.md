---
title: "Timestep control law"
chapter: "05_numerical_integration"
section: "06_timestep_control_law"
section_number: "5.6"
topic: "06_timestep_control_law"
mission_primary: "kernel_reimplementation"
mission_secondary: ["circuit_design_validation"]
related_files:
  - "src/spicelib/analysis/dctran.c"
  - "src/spicelib/analysis/ckttrunc.c"
related_chapters:
  - "../03_analysis_drivers/03_transient_dctran.md"
  - "05_lte_estimation_devtrunc.md"
domain_concepts:
  - "timestep_control"
canonical_chain_tags:
  - "transient_step_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 10
last_updated_from_source_at: "2026-04-09T03:39:07.072860+00:00"
---

# Timestep control law {#timestep-control-law}

## Overview {#overview}

`DCtran` couples **Newton success/failure** with **truncation feedback**:

- Failed Newton rolls time back and divides `CKTdelta` by 8 ([Source: src/spicelib/analysis/dctran.c#L793-L810]).
- Accepted steps call `CKTtrunc` to propose `newdelta`, optionally increasing integration order when truncation allows headroom ([Source: src/spicelib/analysis/dctran.c#L856-L873]).
- `CKTtrunc` merges per-device limits and caps timestep growth relative to the previous value ([Source: src/spicelib/analysis/ckttrunc.c#L33-L53]).

<!-- source: src/spicelib/analysis/dctran.c -->
<!-- source: src/spicelib/analysis/ckttrunc.c -->

## Source Files {#source-files}

- **`src/spicelib/analysis/dctran.c`**
- **`src/spicelib/analysis/ckttrunc.c`**

## Related Chapters {#related-chapters}

- [Transient driver](../03_analysis_drivers/03_transient_dctran.md)

## Canonical Chains {#canonical-chains}

- `transient_step_chain`
