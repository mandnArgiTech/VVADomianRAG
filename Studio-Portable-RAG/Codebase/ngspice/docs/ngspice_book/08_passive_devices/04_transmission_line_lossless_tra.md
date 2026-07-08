---
title: "Lossless transmission line (TRA)"
chapter: "08_passive_devices"
section: "04_transmission_line_lossless_tra"
section_number: "8.4"
topic: "04_transmission_line_lossless_tra"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/spicelib/devices/tra/traload.c"
related_chapters:
  - "../03_analysis_drivers/03_transient_dctran.md"
domain_concepts:
  - "mna_modified_nodal_analysis"
canonical_chain_tags:
  - "transient_step_chain"
numerical_invariants_introduced:
  - "mna_matrix_assembly"
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 7
last_updated_from_source_at: "2026-04-09T03:39:07.072860+00:00"
---

# Lossless transmission line (TRA) {#transmission-line-lossless-tra}

## Overview {#overview}

`TRAload` stamps the constant-delay transmission-line template: conductance links between endpoint and internal nodes plus branch equations tying interface currents ([Source: src/spicelib/devices/tra/traload.c#L18-L45]).

<!-- source: src/spicelib/devices/tra/traload.c -->

## Source Files {#source-files}

- **`src/spicelib/devices/tra/traload.c`**

## Related Chapters {#related-chapters}

- [Transient driver](../03_analysis_drivers/03_transient_dctran.md)
