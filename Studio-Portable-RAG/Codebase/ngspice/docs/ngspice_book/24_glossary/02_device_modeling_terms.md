---
title: "Device modeling terms"
chapter: "24_glossary"
section: "02_device_modeling_terms"
section_number: "24.2"
topic: "02_device_modeling_terms"
mission_primary: "circuit_design_validation"
mission_secondary: ["kernel_reimplementation"]
related_files:
  - "src/include/ngspice/devdefs.h"
  - "src/spicelib/devices/dev.c"
related_chapters:
  - "../07_device_model_contract/README.md"
domain_concepts:
  - "glossary_devices"
canonical_chain_tags:
  - "device_load_dispatch_chain"
numerical_invariants_introduced: []
glossary_terms_introduced:
  - "SPICEdev"
  - "DEVload"
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 11
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Device modeling terms {#device-modeling-terms}

## `SPICEdev` {#spicedev}

Structure describing device metadata plus function pointers (`DEVload`, `DEVacLoad`, `DEVtrunc`, …) registered in `DEVices[]` ([Source: src/include/ngspice/devdefs.h#L47-L120]).

## `DEVload` {#devload}

Per-model stamping routine called from `CKTload` for DC/transient Jacobian assembly ([Source: src/spicelib/analysis/cktload.c#L61-L64]).

## `DEVacLoad` {#devacload}

Complex linearization path used by AC analysis ([Source: ../07_device_model_contract/04_devacload_ac_linearization.md]).

## `DEVtrunc` {#devtrunc}

Supplies LTE estimates for timestep control ([Source: ../07_device_model_contract/05_devtrunc_lte_per_device.md]).

## Model card vs instance {#model-instance}

`.model` lines populate `inpdomod` tables; element lines instantiate `GENinstance` records consumed in `DEVload` ([Source: ../15_parser_and_expansion/02_dotcommand_dispatch.md]).
