---
title: "Capacitor"
chapter: "08_passive_devices"
section: "02_capacitor"
section_number: "8.2"
topic: "02_capacitor"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/spicelib/devices/cap/capload.c"
  - "src/maths/ni/niinteg.c"
related_chapters:
  - "../05_numerical_integration/04_charge_conserving_capacitor_stamps.md"
domain_concepts:
  - "numerical_integration"
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

# Capacitor {#capacitor}

## Overview {#overview}

`CAPload` integrates charge for transient/AC analyses, calling `NIintegrate` to obtain `geq`/`ceq` companions and stamping them symmetrically across the capacitor nodes ([Source: src/spicelib/devices/cap/capload.c#L52-L79]).

<!-- source: src/spicelib/devices/cap/capload.c -->

## Source Files {#source-files}

- **`src/spicelib/devices/cap/capload.c`**
- **`src/maths/ni/niinteg.c`**

## Related Chapters {#related-chapters}

- [Charge-conserving stamps](../05_numerical_integration/04_charge_conserving_capacitor_stamps.md)
