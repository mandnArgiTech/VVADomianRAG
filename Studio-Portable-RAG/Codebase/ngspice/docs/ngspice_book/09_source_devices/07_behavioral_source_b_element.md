---
title: "Behavioral source (B)"
chapter: "09_source_devices"
section: "07_behavioral_source_b_element"
section_number: "9.7"
topic: "07_behavioral_source_b_element"
mission_primary: "kernel_reimplementation"
mission_secondary: ["circuit_design_validation"]
related_files:
  - "src/spicelib/devices/asrc/asrcload.c"
related_chapters:
  - "../15_parser_and_expansion/05_expression_evaluator.md"
domain_concepts:
  - "behavioral_sources"
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

# Behavioral source (B / ASRC) {#behavioral-source-b-element}

## Overview {#overview}

`ASRCload` evaluates arbitrary algebraic expressions stored in `ASRCtree`, allocating derivative buffers sized to the expression arity ([Source: src/spicelib/devices/asrc/asrcload.c#L47-L55]). Temperature coefficients scale the output before linearization ([Source: src/spicelib/devices/asrc/asrcload.c#L41-L45]).

<!-- source: src/spicelib/devices/asrc/asrcload.c -->

## Source Files {#source-files}

- **`src/spicelib/devices/asrc/asrcload.c`**

## Related Chapters {#related-chapters}

- [Expression evaluator](../15_parser_and_expansion/05_expression_evaluator.md)
