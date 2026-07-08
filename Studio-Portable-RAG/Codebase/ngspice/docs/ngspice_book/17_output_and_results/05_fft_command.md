---
title: "FFT command"
chapter: "17_output_and_results"
section: "05_fft_command"
section_number: "17.5"
topic: "05_fft_command"
mission_primary: "circuit_design_validation"
mission_secondary: []
related_files:
  - "src/frontend/com_fft.c"
related_chapters:
  - "../03_analysis_drivers/10_fourier_post_processing.md"
domain_concepts:
  - "fft_post"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 9
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# FFT command {#fft-command}

## `com_fft` {#com-fft}

`com_fft` allocates time-domain buffers, optional windowing, and (when available) `fftw3` plans to transform `dvec` data into frequency spectra ([Source: src/frontend/com_fft.c#L6-L44]).

## Inputs {#inputs}

The command parses vector expressions via `pnode` trees (`names`) just like other nutmeg math commands, ensuring consistent units with the active plot’s scale vector ([Source: src/frontend/com_fft.c#L34-L36]).

## Relation to `.four` {#four}

Deck `.four` is rejected in `INP2dot`; use interactive `fourier`/`fft` instead ([Source: src/spicelib/parser/inp2dot.c#L670-L675]).
