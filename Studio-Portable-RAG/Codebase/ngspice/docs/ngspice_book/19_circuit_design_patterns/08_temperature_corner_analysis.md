---
title: "Temperature corner analysis"
chapter: "19_circuit_design_patterns"
section: "08_temperature_corner_analysis"
section_number: "19.8"
topic: "08_temperature_corner_analysis"
mission_primary: "circuit_design_validation"
mission_secondary: []
related_files:
  - "src/include/ngspice/cktdefs.h"
  - "src/spicelib/parser/inpdoopt.c"
related_chapters:
  - "../18_options_and_tolerances/06_temperature_options.md"
domain_concepts:
  - "temp_corners"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 9
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Temperature corner analysis {#temperature-corner-analysis}

## Simulator state {#simulator-state}

`CKTtemp` drives `DEVtemperature` updates across the device table ([Source: src/include/ngspice/cktdefs.h#L93-L95]).

## Setting corners {#setting-corners}

Use `.options TEMP=…` (parsed via `INPdoOpts`) rather than the legacy `.temp` card, which `INP2dot` ignores ([Source: src/spicelib/parser/inpdoopt.c#L46-L68], [Source: src/spicelib/parser/inp2dot.c#L652-L658]).

## Workflow {#workflow}

Run a matrix of `.options` blocks inside `.control` or spawn batch jobs per corner, logging `.measure` outputs for slope analysis.
