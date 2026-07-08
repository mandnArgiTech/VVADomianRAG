---
title: "Transfer function (TFanal)"
chapter: "03_analysis_drivers"
section: "07_transfer_function_tfan"
section_number: "3.7"
topic: "07_transfer_function_tfan"
mission_primary: "kernel_reimplementation"
mission_secondary: ["circuit_design_validation"]
related_files:
  - "src/spicelib/analysis/tfanal.c"
related_chapters:
  - "../14_netlist_grammar/08_dot_tf_dot_sens_dot_pz.md"
domain_concepts:
  - "transfer_function_analysis"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 8
last_updated_from_source_at: "2026-04-09T03:39:07.072860+00:00"
---

# Transfer function (TFanal) {#transfer-function-tfan}

## Overview {#overview}

`TFanal` begins by solving the DC operating point with `CKTop` using the same `MODEINITJCT` / `MODEINITFLOAT` pair as other DC analyses ([Source: src/spicelib/analysis/tfanal.c#L43-L47]). After convergence, it locates the requested input source (`CKTfndDev`) and computes small-signal gain, input impedance, and output impedance arrays pushed through the front-end plotting interface ([Source: src/spicelib/analysis/tfanal.c#L49-L55]).

<!-- source: src/spicelib/analysis/tfanal.c -->

## Source Files {#source-files}

- **`src/spicelib/analysis/tfanal.c`**

## Related Chapters {#related-chapters}

- [.tf / .sens / .pz grammar](../14_netlist_grammar/08_dot_tf_dot_sens_dot_pz.md)
