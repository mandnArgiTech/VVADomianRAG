---
title: "Temperature options"
chapter: "18_options_and_tolerances"
section: "06_temperature_options"
section_number: "18.6"
topic: "06_temperature_options"
mission_primary: "circuit_design_validation"
mission_secondary: []
related_files:
  - "src/include/ngspice/cktdefs.h"
  - "src/spicelib/parser/inp2dot.c"
related_chapters:
  - "../07_device_model_contract/08_devtemperature_temp_resolution.md"
domain_concepts:
  - "temperature_options"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 9
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Temperature options {#temperature-options}

## Circuit temperature {#circuit-temperature}

`CKTtemp` and derived `CKTvt` track the absolute temperature used during model evaluation ([Source: src/include/ngspice/cktdefs.h#L93-L95]).

## Deprecated `.temp` card {#deprecated-temp}

`INP2dot` still recognizes `.temp` but the branch exits without attaching analysis jobs—users should prefer `.options TEMP=…` as hinted in comments ([Source: src/spicelib/parser/inp2dot.c#L652-L658]).

## Device hook {#device-hook}

Each `SPICEdev` may implement `DEVtemperature` to remap parameters vs `CKTtemp` ([Source: ../07_device_model_contract/08_devtemperature_temp_resolution.md]).
