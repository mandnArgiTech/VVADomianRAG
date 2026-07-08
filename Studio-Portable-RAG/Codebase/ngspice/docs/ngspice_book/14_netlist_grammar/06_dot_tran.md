---
title: ".tran"
chapter: "14_netlist_grammar"
section: "06_dot_tran"
section_number: "14.6"
topic: "06_dot_tran"
mission_primary: "circuit_design_validation"
mission_secondary: ["kernel_reimplementation"]
related_files:
  - "src/spicelib/parser/inp2dot.c"
related_chapters:
  - "../03_analysis_drivers/03_transient_dctran.md"
  - "../05_numerical_integration/06_timestep_control_law.md"
domain_concepts:
  - "transient_analysis"
canonical_chain_tags:
  - "transient_step_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 9
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# .tran {#dot-tran}

## Required parameters {#required}

`dot_tran` reads `tstep` and `tstop`, then optionally `tstart`, `tmax`, and the `uic` flag ([Source: src/spicelib/parser/inp2dot.c#L363-L394]). Unknown trailing tokens produce `LITERR` diagnostics ([Source: src/spicelib/parser/inp2dot.c#L392-L393]).

## Job creation {#job}

The `"TRAN"` analysis is registered through `newAnalysis` when supported ([Source: src/spicelib/parser/inp2dot.c#L364-L369]).

## Dispatch {#dispatch}

 Routed from `INP2dot` on `.tran` ([Source: src/spicelib/parser/inp2dot.c#L690-L692]).
