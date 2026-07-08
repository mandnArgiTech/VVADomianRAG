---
title: "AC small-signal (ACan)"
chapter: "03_analysis_drivers"
section: "04_ac_small_signal_acan"
section_number: "3.4"
topic: "04_ac_small_signal_acan"
mission_primary: "kernel_reimplementation"
mission_secondary: ["circuit_design_validation"]
related_files:
  - "src/spicelib/analysis/acan.c"
related_chapters:
  - "../07_device_model_contract/04_devacload_ac_linearization.md"
  - "../14_netlist_grammar/05_dot_ac.md"
domain_concepts:
  - "ac_small_signal_analysis"
canonical_chain_tags:
  - "ac_analysis_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 10
last_updated_from_source_at: "2026-04-09T03:39:07.072860+00:00"
---

# AC small-signal (ACan) {#ac-small-signal-acan}

## Overview {#overview}

`ACan` walks the frequency list stored in the `ACAN` job, maintaining statistics macros `INIT_STATS` / `UPDATE_STATS` for load, factor, and solve time attribution ([Source: src/spicelib/analysis/acan.c#L22-L39, L42-L44]).

The driver assumes a prior DC solution (or performs linearization consistent with the job) before repeatedly stamping complex Jacobians via `DEVacLoad` and solving with the complex sparse path (`SMPc*` helpers in the SMP layer).

<!-- source: src/spicelib/analysis/acan.c -->

## What This Driver Does {#what-it-does}

Turns the **linearized** MNA system across a frequency sweep into plotted outputs (gain/phase, impedances, etc.), relying on device `DEVacLoad` implementations.

## Source Files {#source-files}

- **`src/spicelib/analysis/acan.c`**

## Related Chapters {#related-chapters}

- [DEVacLoad](../07_device_model_contract/04_devacload_ac_linearization.md)
- [.ac grammar](../14_netlist_grammar/05_dot_ac.md)

## Canonical Chains {#canonical-chains}

- `ac_analysis_chain`
