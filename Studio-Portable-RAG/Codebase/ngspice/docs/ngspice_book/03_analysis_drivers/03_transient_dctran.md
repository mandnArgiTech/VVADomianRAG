---
title: "Transient (DCtran)"
chapter: "03_analysis_drivers"
section: "03_transient_dctran"
section_number: "3.3"
topic: "03_transient_dctran"
mission_primary: "kernel_reimplementation"
mission_secondary: ["circuit_design_validation"]
related_files:
  - "src/spicelib/analysis/dctran.c"
  - "src/spicelib/analysis/ckttrunc.c"
  - "src/spicelib/devices/cktaccept.c"
related_chapters:
  - "../02_numerical_kernel_core/02_newton_raphson_iteration_niiter.md"
  - "../05_numerical_integration/06_timestep_control_law.md"
  - "../23_canonical_chains_reference/02_transient_step_chain.md"
domain_concepts:
  - "transient_analysis"
canonical_chain_tags:
  - "transient_step_chain"
numerical_invariants_introduced:
  - "newton_raphson_iteration"
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 14
last_updated_from_source_at: "2026-04-09T03:39:07.072860+00:00"
---

# Transient (DCtran) {#transient-dctran}

## Overview {#overview}

`DCtran` advances `CKTtime` with adaptive steps. After updating integration coefficients (`NIcomCof`) and optional predictor hooks, each trial timepoint calls `NIiter` with `ckt->CKTtranMaxIter` ([Source: src/spicelib/analysis/dctran.c#L730-L770]).

If Newton fails, the step rolls back (`CKTtime -= CKTdelta`), shrinks `CKTdelta` by factor 8, and resets integration order to 1 ([Source: src/spicelib/analysis/dctran.c#L793-L810]). Successful steps invoke `CKTtrunc` to propose the next timestep, possibly promoting order to 2 when truncation allows ([Source: src/spicelib/analysis/dctran.c#L856-L873]).

Accepted steps call `CKTaccept` to run per-device acceptance hooks ([Source: src/spicelib/analysis/dctran.c#L399], see [Source: src/spicelib/devices/cktaccept.c#L19-L37]).

<!-- source: src/spicelib/analysis/dctran.c -->
<!-- source: src/spicelib/analysis/ckttrunc.c -->
<!-- source: src/spicelib/devices/cktaccept.c -->

## Numerical Invariants {#invariants}

| Invariant | Specification | Source |
|-----------|---------------|--------|
| Inner NR budget | `CKTtranMaxIter` passed to `NIiter` | [Source: src/spicelib/analysis/dctran.c#L770] |
| Failure backoff | Divide `CKTdelta` by 8 | [Source: src/spicelib/analysis/dctran.c#L802] |
| LTE aggregation | `CKTtrunc` min-reduces candidate step across devices | [Source: src/spicelib/analysis/ckttrunc.c#L33-L53] |

## Source Files {#source-files}

- **`src/spicelib/analysis/dctran.c`**
- **`src/spicelib/analysis/ckttrunc.c`**
- **`src/spicelib/devices/cktaccept.c`**

## Related Chapters {#related-chapters}

- [NIiter](../02_numerical_kernel_core/02_newton_raphson_iteration_niiter.md)
- [Timestep control](../05_numerical_integration/06_timestep_control_law.md)
- [Transient chain](../23_canonical_chains_reference/02_transient_step_chain.md)

## Canonical Chains {#canonical-chains}

- `transient_step_chain`
