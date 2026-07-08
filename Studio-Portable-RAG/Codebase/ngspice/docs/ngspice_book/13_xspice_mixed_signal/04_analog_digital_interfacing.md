---
title: "Analog/digital interfacing"
chapter: "13_xspice_mixed_signal"
section: "04_analog_digital_interfacing"
section_number: "13.4"
topic: "04_analog_digital_interfacing"
mission_primary: "kernel_reimplementation"
mission_secondary: ["circuit_design_validation"]
related_files:
  - "src/spicelib/analysis/dcop.c"
  - "src/spicelib/analysis/dctran.c"
related_chapters:
  - "01_xspice_event_driven_overview.md"
domain_concepts:
  - "xspice_mixed_signal"
canonical_chain_tags:
  - "transient_step_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "ngspice core developer"
estimated_reading_minutes: 8
last_updated_from_source_at: "2026-04-09T03:39:07.072860+00:00"
---

# Analog/digital interfacing {#analog-digital-interfacing}

## Overview {#overview}

Mixed-signal coupling shows up directly in analysis drivers:

- `DCop` may replace the classical `CKTop` flow with `EVTop` when event instances exist ([Source: src/spicelib/analysis/dcop.c#L67-L78]).
- `DCtran` alternates Newton solves with `EVTcall_hybrids` and consults `g_mif_info.breakpoint` for time rollback ([Source: src/spicelib/analysis/dctran.c#L770-L826]).

<!-- source: src/spicelib/analysis/dcop.c -->
<!-- source: src/spicelib/analysis/dctran.c -->

## Source Files {#source-files}

- **`src/spicelib/analysis/dcop.c`**
- **`src/spicelib/analysis/dctran.c`**

## Related Chapters {#related-chapters}

- [XSPICE overview](01_xspice_event_driven_overview.md)
