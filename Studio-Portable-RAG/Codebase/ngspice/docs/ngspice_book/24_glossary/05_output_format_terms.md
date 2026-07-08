---
title: "Output format terms"
chapter: "24_glossary"
section: "05_output_format_terms"
section_number: "24.5"
topic: "05_output_format_terms"
mission_primary: "circuit_design_validation"
mission_secondary: []
related_files:
  - "src/include/ngspice/dvec.h"
  - "src/frontend/rawfile.c"
related_chapters:
  - "../17_output_and_results/README.md"
domain_concepts:
  - "glossary_output"
canonical_chain_tags:
  - "raw_output_consumption_chain"
numerical_invariants_introduced: []
glossary_terms_introduced:
  - "dvec"
  - "raw_write"
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 10
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Output format terms {#output-format-terms}

## `dvec` {#dvec}

Vector of simulation data (real or complex) with dimensional metadata ([Source: src/include/ngspice/dvec.h#L37-L59]).

## `plot` {#plot}

Container linking title, scale vector, and `dvec` list ([Source: src/include/ngspice/plot.h#L13-L28]).

## Raw file {#raw-file}

Serialized `plot` produced by `raw_write` ([Source: src/frontend/rawfile.c#L34-L57]).

## `.measure` {#measure}

Post-simulation scalar extraction invoked from `dosim` ([Source: src/frontend/runcoms.c#L359-L361]).

## FFT vector {#fft-vector}

`com_fft` transforms time-domain `dvec` data into spectra ([Source: src/frontend/com_fft.c#L26-L35]).
