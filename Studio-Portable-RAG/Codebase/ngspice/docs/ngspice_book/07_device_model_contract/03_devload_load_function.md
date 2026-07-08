---
title: "DEVload"
chapter: "07_device_model_contract"
section: "03_devload_load_function"
section_number: "7.3"
topic: "03_devload_load_function"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/include/ngspice/devdefs.h"
  - "src/spicelib/analysis/cktload.c"
  - "src/spicelib/devices/bsim4/bsim4init.c"
related_chapters:
  - "../02_numerical_kernel_core/01_circuit_load_dispatch_cktload.md"
domain_concepts:
  - "mna_modified_nodal_analysis"
canonical_chain_tags:
  - "device_load_dispatch_chain"
numerical_invariants_introduced:
  - "mna_matrix_assembly"
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 8
last_updated_from_source_at: "2026-04-09T03:39:07.072860+00:00"
---

# DEVload {#devload-load-function}

## Overview {#overview}

`DEVload` is the resistive Jacobian/RHS stamper invoked from `CKTload` every Newton iteration. Its signature is `int (*DEVload)(GENmodel*, CKTcircuit*)` ([Source: src/include/ngspice/devdefs.h#L54-L55]). BSIM4 registers `BSIM4load` ([Source: src/spicelib/devices/bsim4/bsim4init.c#L45]).

<!-- source: src/include/ngspice/devdefs.h -->
<!-- source: src/spicelib/analysis/cktload.c -->

## Contract {#contract}

Implementations must:

- Stamp into the shared `SMPmatrix` referenced by `ckt->CKTmatrix`.
- Update `ckt->CKTrhs` consistently with KCL.
- Set `ckt->CKTnoncon` when internal heuristics decide the iterate is unreliable ([Source: src/spicelib/analysis/cktload.c#L64-L65]).

## Dispatch Reminder {#dispatch}

`CKTload` iterates device indices and skips NULL heads ([Source: src/spicelib/analysis/cktload.c#L61-L63]).

## Source Files {#source-files}

- **`src/include/ngspice/devdefs.h`**
- **`src/spicelib/analysis/cktload.c`**

## Related Chapters {#related-chapters}

- [CKTload dispatch](../02_numerical_kernel_core/01_circuit_load_dispatch_cktload.md)
