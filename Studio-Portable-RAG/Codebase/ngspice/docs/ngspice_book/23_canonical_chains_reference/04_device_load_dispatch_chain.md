---
title: "Device load dispatch chain"
chapter: "23_canonical_chains_reference"
section: "04_device_load_dispatch_chain"
section_number: "23.4"
topic: "device_load_dispatch_chain"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/spicelib/analysis/cktload.c"
  - "src/include/ngspice/devdefs.h"
  - "src/spicelib/devices/dev.c"
  - "src/spicelib/devices/bsim4/b4ld.c"
related_chapters:
  - "../02_numerical_kernel_core/01_circuit_load_dispatch_cktload.md"
  - "../07_device_model_contract/03_devload_load_function.md"
domain_concepts:
  - "device_model_contract"
canonical_chain_tags:
  - "device_load_dispatch_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 7
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Device load dispatch chain {#device-load-dispatch-chain}

## Summary {#summary}

`CKTload` walks `DEVices[]`, invoking each non-empty model list’s `DEVload` ([Source: src/spicelib/analysis/cktload.c#L61-L75]). BSIM4’s `BSIM4load` illustrates a concrete implementation target ([Source: src/spicelib/devices/bsim4/b4ld.c#L72]).

## Stages {#stages}

`cktload_dispatch` → `devices_table_lookup` → `devload_call` (`rag_index.json`).

## Deep dives {#deep-dives}

- [CKTload](../02_numerical_kernel_core/01_circuit_load_dispatch_cktload.md)
- [DEVload](../07_device_model_contract/03_devload_load_function.md)
