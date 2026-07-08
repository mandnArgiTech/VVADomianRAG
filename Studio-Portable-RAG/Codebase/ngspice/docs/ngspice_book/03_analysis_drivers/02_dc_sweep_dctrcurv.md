---
title: "DC sweep (DCtrCurv)"
chapter: "03_analysis_drivers"
section: "02_dc_sweep_dctrcurv"
section_number: "3.2"
topic: "02_dc_sweep_dctrcurv"
mission_primary: "kernel_reimplementation"
mission_secondary: ["circuit_design_validation"]
related_files:
  - "src/spicelib/analysis/dctrcurv.c"
related_chapters:
  - "01_dc_operating_point_dcop.md"
  - "../14_netlist_grammar/04_dot_op_dot_dc.md"
domain_concepts:
  - "dc_sweep"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 9
last_updated_from_source_at: "2026-04-09T03:39:07.072860+00:00"
---

# DC sweep (DCtrCurv) {#dc-sweep-dctrcurv}

## Overview {#overview}

`DCtrCurv` implements nested DC sweeps driven by a `TRCV` job structure: it resolves device type codes for resistors and sources (`CKTtypelook`), manages sweep state in `job->TRCVnestState`, and walks the multi-dimensional sweep space while emitting plots ([Source: src/spicelib/analysis/dctrcurv.c#L33-L80]).

Each sweep point ultimately relies on the same `CKTop` / `NIiter` machinery as a single DC operating point, but repeated with perturbed source values.

<!-- source: src/spicelib/analysis/dctrcurv.c -->

## What This Driver Does {#what-it-does}

Coordinates **outer** sweep loops around **inner** Newton solves—useful when correlating `.dc` netlist directives with simulator behavior.

## Source Files {#source-files}

- **`src/spicelib/analysis/dctrcurv.c`**

## Related Chapters {#related-chapters}

- [DC operating point](01_dc_operating_point_dcop.md)
- [.dc grammar](../14_netlist_grammar/04_dot_op_dot_dc.md)
