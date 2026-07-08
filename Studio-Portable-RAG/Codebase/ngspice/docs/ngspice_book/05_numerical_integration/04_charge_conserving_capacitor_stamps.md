---
title: "Charge-conserving capacitor stamps"
chapter: "05_numerical_integration"
section: "04_charge_conserving_capacitor_stamps"
section_number: "5.4"
topic: "04_charge_conserving_capacitor_stamps"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/spicelib/devices/cap/capload.c"
  - "src/maths/ni/niinteg.c"
related_chapters:
  - "../08_passive_devices/02_capacitor.md"
domain_concepts:
  - "mna_modified_nodal_analysis"
canonical_chain_tags:
  - "transient_step_chain"
numerical_invariants_introduced:
  - "mna_matrix_assembly"
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 9
last_updated_from_source_at: "2026-04-09T03:39:07.072860+00:00"
---

# Charge-conserving capacitor stamps {#charge-conserving-capacitor-stamps}

## Overview {#overview}

Linear capacitors update stored charge `CAPqcap` each transient load, then call `NIintegrate` to obtain companion conductance `geq` and current source `ceq`, stamping the symmetric MNA pattern into the sparse matrix ([Source: src/spicelib/devices/cap/capload.c#L52-L79]).

`NIintegrate` finishes by setting `*ceq = ccap - CKTtag[0]*q` and `*geq = CKTtag[0]*cap` ([Source: src/maths/ni/niinteg.c#L77-L78]).

<!-- source: src/spicelib/devices/cap/capload.c -->
<!-- source: src/maths/ni/niinteg.c -->

## Source Files {#source-files}

- **`src/spicelib/devices/cap/capload.c`**
- **`src/maths/ni/niinteg.c`**

## Related Chapters {#related-chapters}

- [Capacitor device](../08_passive_devices/02_capacitor.md)
