---
title: "Inductor and mutual"
chapter: "08_passive_devices"
section: "03_inductor_and_mutual"
section_number: "8.3"
topic: "03_inductor_and_mutual"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/spicelib/devices/ind/indload.c"
related_chapters:
  - "../05_numerical_integration/01_trapezoidal_integration.md"
domain_concepts:
  - "mna_modified_nodal_analysis"
canonical_chain_tags:
  - "transient_step_chain"
numerical_invariants_introduced:
  - "mna_matrix_assembly"
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 8
last_updated_from_source_at: "2026-04-09T03:39:07.072860+00:00"
---

# Inductor and mutual {#inductor-and-mutual}

## Overview {#overview}

`INDload` integrates flux linkage for each inductor instance, using branch currents from `CKTrhsOld` unless UIC initialization applies, then feeds the companion model into the MNA system ([Source: src/spicelib/devices/ind/indload.c#L18-L51]). When compiled with `MUTUAL`, the file continues into coupled-inductor stamping (`MUT` device types, [Source: src/spicelib/devices/ind/indload.c#L52-L55]).

<!-- source: src/spicelib/devices/ind/indload.c -->

## Source Files {#source-files}

- **`src/spicelib/devices/ind/indload.c`**

## Related Chapters {#related-chapters}

- [Integration methods](../05_numerical_integration/01_trapezoidal_integration.md)
