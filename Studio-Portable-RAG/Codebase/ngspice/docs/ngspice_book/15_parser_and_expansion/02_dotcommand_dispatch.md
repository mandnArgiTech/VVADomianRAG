---
title: "Dot-command dispatch"
chapter: "15_parser_and_expansion"
section: "02_dotcommand_dispatch"
section_number: "15.2"
topic: "02_dotcommand_dispatch"
mission_primary: "circuit_design_validation"
mission_secondary: ["kernel_reimplementation"]
related_files:
  - "src/spicelib/parser/inp2dot.c"
related_chapters:
  - "../14_netlist_grammar/03_dotcommand_overview.md"
  - "../03_analysis_drivers/README.md"
domain_concepts:
  - "dot_dispatch"
canonical_chain_tags:
  - "netlist_to_simulation_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 10
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Dot-command dispatch {#dotcommand-dispatch}

## `INP2dot` switchboard {#inp2dot}

`INP2dot` compares the first token against the supported `.` directives and delegates to helpers such as `dot_op`, `dot_dc`, `dot_ac`, `dot_tran`, `dot_noise`, `dot_options`, etc. ([Source: src/spicelib/parser/inp2dot.c#L631-L727]).

## Analysis registration {#analysis-registration}

Each helper calls `ft_find_analysis("<NAME>")` and, on success, `newAnalysis` followed by `INPapName`/`INPgetValue` pairs that populate the `JOB` structure ([Source: src/spicelib/parser/inp2dot.c#L127-L134], [Source: src/spicelib/parser/inp2dot.c#L350-L369]).

## Early termination {#end}

`.end` returns `rtn = 1` to signal that no additional cards should be processed ([Source: src/spicelib/parser/inp2dot.c#L705-L709]).
