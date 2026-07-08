---
title: "Sensitivity (sens_sens / cktsens)"
chapter: "03_analysis_drivers"
section: "08_sensitivity_adjoint_senan"
section_number: "3.8"
topic: "08_sensitivity_adjoint_senan"
mission_primary: "kernel_reimplementation"
mission_secondary: ["circuit_design_validation"]
related_files:
  - "src/spicelib/analysis/cktsens.c"
related_chapters:
  - "../07_device_model_contract/09_devsens_sensitivity_per_device.md"
  - "../14_netlist_grammar/08_dot_tf_dot_sens_dot_pz.md"
domain_concepts:
  - "sensitivity_analysis"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 11
last_updated_from_source_at: "2026-04-09T03:39:07.072860+00:00"
---

# Sensitivity (`sens_sens`) {#sensitivity-adjoint-senan}

## Overview {#overview}

`cktsens.c` implements adjoint-style DC and AC sensitivity. The documented algorithm:

1. Determine DC operating point (`CKTop`).
2. For each frequency (AC mode), call `NIacIter`.
3. For each swept parameter, build perturbation matrices and solve \(\Delta E = Y^{-1}(\Delta Y E - \Delta I)\).

([Source: src/spicelib/analysis/cktsens.c#L48-L59])

The exported driver is `sens_sens(CKTcircuit *ckt, int restart)` ([Source: src/spicelib/analysis/cktsens.c#L63-L65]).

<!-- source: src/spicelib/analysis/cktsens.c -->

## Source Files {#source-files}

- **`src/spicelib/analysis/cktsens.c`**

## Related Chapters {#related-chapters}

- [DEVsens hooks](../07_device_model_contract/09_devsens_sensitivity_per_device.md)
- [.sens grammar](../14_netlist_grammar/08_dot_tf_dot_sens_dot_pz.md)
