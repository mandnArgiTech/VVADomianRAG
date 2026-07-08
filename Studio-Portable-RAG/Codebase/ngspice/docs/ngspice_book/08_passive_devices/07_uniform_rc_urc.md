---
title: "Uniform RC (URC)"
chapter: "08_passive_devices"
section: "07_uniform_rc_urc"
section_number: "8.7"
topic: "07_uniform_rc_urc"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/spicelib/devices/urc/urcsetup.c"
  - "src/spicelib/devices/urc/urc.c"
related_chapters:
  - "01_resistor.md"
  - "02_capacitor.md"
domain_concepts:
  - "mna_modified_nodal_analysis"
canonical_chain_tags: []
numerical_invariants_introduced:
  - "mna_matrix_assembly"
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 7
last_updated_from_source_at: "2026-04-09T03:39:07.072860+00:00"
---

# Uniform RC (URC) {#uniform-rc-urc}

## Overview {#overview}

The URC device does not expose a monolithic `URCload` in the small `urc/` translation unit; instead `URCsetup` **expands** each uniform RC line into a ladder of native resistors, capacitors, and diodes based on `.model urc` parameters ([Source: src/spicelib/devices/urc/urcsetup.c#L15-L18]).

Parameter metadata (`URCpTable`, `URCmPTable`) lives in `urc.c` ([Source: src/spicelib/devices/urc/urc.c#L11-L27]).

<!-- source: src/spicelib/devices/urc/urcsetup.c -->
<!-- source: src/spicelib/devices/urc/urc.c -->

## Source Files {#source-files}

- **`src/spicelib/devices/urc/urcsetup.c`**
- **`src/spicelib/devices/urc/urc.c`**

## Related Chapters {#related-chapters}

- [Resistor](01_resistor.md)
- [Capacitor](02_capacitor.md)
