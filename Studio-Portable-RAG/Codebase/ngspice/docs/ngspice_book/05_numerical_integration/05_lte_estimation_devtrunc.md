---
title: "LTE estimation (DEVtrunc)"
chapter: "05_numerical_integration"
section: "05_lte_estimation_devtrunc"
section_number: "5.5"
topic: "05_lte_estimation_devtrunc"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/spicelib/analysis/ckttrunc.c"
related_chapters:
  - "../07_device_model_contract/05_devtrunc_lte_per_device.md"
domain_concepts:
  - "lte_estimation"
canonical_chain_tags:
  - "transient_step_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 7
last_updated_from_source_at: "2026-04-09T03:39:07.072860+00:00"
---

# LTE estimation (`CKTtrunc`) {#lte-estimation-devtrunc}

## Overview {#overview}

`CKTtrunc` iterates every device with a non-NULL `DEVtrunc`, letting each shrink a local `timetemp` candidate. The smallest request wins; the driver then caps growth: `*timeStep = MIN(2 * *timeStep, timetemp)` ([Source: src/spicelib/analysis/ckttrunc.c#L33-L53]).

When `NEWTRUNC` is defined, an alternate per-node path compiles in the same file ([Source: src/spicelib/analysis/ckttrunc.c#L57-L70]).

<!-- source: src/spicelib/analysis/ckttrunc.c -->

## Source Files {#source-files}

- **`src/spicelib/analysis/ckttrunc.c`**

## Related Chapters {#related-chapters}

- [DEVtrunc](../07_device_model_contract/05_devtrunc_lte_per_device.md)

## Canonical Chains {#canonical-chains}

- `transient_step_chain`
