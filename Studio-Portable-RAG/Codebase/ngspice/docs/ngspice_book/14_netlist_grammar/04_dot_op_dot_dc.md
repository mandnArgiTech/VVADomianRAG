---
title: ".op and .dc"
chapter: "14_netlist_grammar"
section: "04_dot_op_dot_dc"
section_number: "14.4"
topic: "04_dot_op_dot_dc"
mission_primary: "circuit_design_validation"
mission_secondary: ["kernel_reimplementation"]
related_files:
  - "src/spicelib/parser/inp2dot.c"
related_chapters:
  - "../03_analysis_drivers/01_dc_operating_point_dcop.md"
  - "../03_analysis_drivers/02_dc_sweep_dctrcurv.md"
domain_concepts:
  - "dc_analysis"
canonical_chain_tags:
  - "dc_operating_point_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 9
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# .op and .dc {#dot-op-dot-dc}

## `.op` — operating point job {#dot-op}

`dot_op` registers the `"OP"` analysis through `ft_find_analysis` and `newAnalysis` with the human-readable label `"Operating Point"` ([Source: src/spicelib/parser/inp2dot.c#L127-L134]). No sweep parameters are attached; the driver solves a single NR problem.

## `.dc` — source sweep {#dot-dc}

`dot_dc` allocates a `"DC"` (`DC transfer characteristic`) job, binds the first source name (`name1`) plus `start1/stop1/step1`, and optionally nests a second source (`name2` …) ([Source: src/spicelib/parser/inp2dot.c#L255-L284]). This mirrors classic SPICE nested sweep syntax.

## Dispatch {#dispatch}

`INP2dot` routes `.op` and `.dc` tokens to those helpers ([Source: src/spicelib/parser/inp2dot.c#L659-L686]).
