---
title: "Noise analysis (NOISEan)"
chapter: "03_analysis_drivers"
section: "05_noise_analysis_noisean"
section_number: "3.5"
topic: "05_noise_analysis_noisean"
mission_primary: "kernel_reimplementation"
mission_secondary: ["circuit_design_validation"]
related_files:
  - "src/spicelib/analysis/noisean.c"
related_chapters:
  - "../07_device_model_contract/10_devnoise_noise_psd_per_device.md"
  - "../14_netlist_grammar/07_dot_noise_dot_disto.md"
domain_concepts:
  - "noise_analysis"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 9
last_updated_from_source_at: "2026-04-09T03:39:07.072860+00:00"
---

# Noise analysis (NOISEan) {#noise-analysis-noisean}

## Overview {#overview}

`NOISEan` evaluates integrated noise at a chosen output pair (`job->output`, `job->outputRef`) driven by an input reference source `job->input`. It validates that the referenced source supports AC excitation (`VSRCacGiven` / `ISRCacGiven`) before proceeding ([Source: src/spicelib/analysis/noisean.c#L39-L59]).

The routine allocates a persistent `Ndata` workspace (`static Ndata *data`) to support long sweeps and interactive interruption ([Source: src/spicelib/analysis/noisean.c#L24-L29]).

<!-- source: src/spicelib/analysis/noisean.c -->

## Source Files {#source-files}

- **`src/spicelib/analysis/noisean.c`**

## Related Chapters {#related-chapters}

- [DEVnoise](../07_device_model_contract/10_devnoise_noise_psd_per_device.md)
- [.noise / .disto grammar](../14_netlist_grammar/07_dot_noise_dot_disto.md)
