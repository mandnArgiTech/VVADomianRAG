---
title: "Fourier post-processing"
chapter: "03_analysis_drivers"
section: "10_fourier_post_processing"
section_number: "3.10"
topic: "10_fourier_post_processing"
mission_primary: "circuit_design_validation"
mission_secondary: ["kernel_reimplementation"]
related_files:
  - "src/frontend/fourier.c"
  - "src/frontend/dotcards.c"
related_chapters:
  - "../17_output_and_results/05_fft_command.md"
  - "../16_command_interpreter/README.md"
domain_concepts: []
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 8
last_updated_from_source_at: "2026-04-09T03:39:07.072860+00:00"
---

# Fourier post-processing {#fourier-post-processing}

## Overview {#overview}

Harmonic analysis is **not** part of the transient Jacobian loop. Instead, the `fourier` command (and legacy `.fourier` dot lines when honored) operates on completed simulation vectors: it interpolates data onto a uniform grid when needed and calls `CKTfour` to extract magnitudes/phases ([Source: src/frontend/fourier.c#L6-L47]).

`dotcards.c` routes `.fourier` handling to `fourier()` when rawfiles are not suppressing it ([Source: src/frontend/dotcards.c#L348-L358]).

<!-- source: src/frontend/fourier.c -->
<!-- source: src/frontend/dotcards.c -->

## Mission Note {#mission-note}

Circuit-design agents should treat Fourier as a **post-process** on `plot` data, whereas kernel reimplementers can ignore it for time-stepping correctness.

## Source Files {#source-files}

- **`src/frontend/fourier.c`**
- **`src/frontend/dotcards.c`**

## Related Chapters {#related-chapters}

- [FFT command](../17_output_and_results/05_fft_command.md)
- [Command interpreter](../16_command_interpreter/README.md)
