---
title: "XSPICE event-driven overview"
chapter: "13_xspice_mixed_signal"
section: "01_xspice_event_driven_overview"
section_number: "13.1"
topic: "01_xspice_event_driven_overview"
mission_primary: "kernel_reimplementation"
mission_secondary: ["circuit_design_validation"]
related_files:
  - "src/include/ngspice/evt.h"
  - "src/include/ngspice/mif.h"
related_chapters:
  - "../03_analysis_drivers/01_dc_operating_point_dcop.md"
domain_concepts:
  - "xspice_mixed_signal"
canonical_chain_tags:
  - "dc_operating_point_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "ngspice core developer"
estimated_reading_minutes: 9
last_updated_from_source_at: "2026-04-09T03:39:07.065678+00:00"
---

# XSPICE event-driven overview {#xspice-event-driven-overview}

## Overview {#overview}

XSPICE extends `CKTcircuit` with event-driven state housed in `ckt->evt` (see `Evt_Ckt_Data_t` in `evt.h`, [Source: src/include/ngspice/evt.h#L24-L29]). The Model-Interface (MIF) package shares global context through `Mif_Info_t`, including breakpoint metadata and auto-partial flags ([Source: src/include/ngspice/mif.h#L49-L77]).

Mission-1 traces show XSPICE altering DC (`EVTop` path in `dcop.c`, [Source: src/spicelib/analysis/dcop.c#L67-L78]) and transient (`g_mif_info` breakpoints in `dctran.c`, [Source: src/spicelib/analysis/dctran.c#L742-L826]).

<!-- source: src/include/ngspice/evt.h -->
<!-- source: src/include/ngspice/mif.h -->

## Source Files {#source-files}

- **`src/include/ngspice/evt.h`**
- **`src/include/ngspice/mif.h`**

## Related Chapters {#related-chapters}

- [DC operating point](../03_analysis_drivers/01_dc_operating_point_dcop.md)
