---
title: "Event node types"
chapter: "13_xspice_mixed_signal"
section: "02_event_node_types"
section_number: "13.2"
topic: "02_event_node_types"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/include/ngspice/evt.h"
related_chapters:
  - "01_xspice_event_driven_overview.md"
domain_concepts:
  - "xspice_mixed_signal"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "ngspice core developer"
estimated_reading_minutes: 7
last_updated_from_source_at: "2026-04-09T03:39:07.065678+00:00"
---

# Event node types {#event-node-types}

## Overview {#overview}

`evt.h` defines linked structures (`Evt_Output_Info_t`, etc.) that describe how event nodes connect to the analog MNA system ([Source: src/include/ngspice/evt.h#L57-L60]). Each output record tracks node indices and sub-indices for mixed-signal coupling.

<!-- source: src/include/ngspice/evt.h -->

## Source Files {#source-files}

- **`src/include/ngspice/evt.h`**

## Related Chapters {#related-chapters}

- [XSPICE overview](01_xspice_event_driven_overview.md)
