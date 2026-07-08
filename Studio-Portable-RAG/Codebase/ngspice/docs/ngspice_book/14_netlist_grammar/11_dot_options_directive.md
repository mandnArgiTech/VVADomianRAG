---
title: ".options directive"
chapter: "14_netlist_grammar"
section: "11_dot_options_directive"
section_number: "14.11"
topic: "11_dot_options_directive"
mission_primary: "circuit_design_validation"
mission_secondary: ["kernel_reimplementation"]
related_files:
  - "src/spicelib/parser/inp2dot.c"
  - "src/spicelib/parser/inpdoopt.c"
related_chapters:
  - "../18_options_and_tolerances/01_options_overview.md"
domain_concepts:
  - "spice_options"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 9
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# .options directive {#dot-options-directive}

## Dispatch {#dispatch}

`.options`, `.option`, and `.opt` synonyms all route to `dot_options`, which forwards parsing to `INPdoOpts` ([Source: src/spicelib/parser/inp2dot.c#L723-L727], [Source: src/spicelib/parser/inp2dot.c#L614-L627]).

## Token loop {#token-loop}

`INPdoOpts` strips the leading `.option` token, then repeatedly reads `name = value` pairs, resolves them through `ft_find_analysis_parm`, and applies simulator parameters with `ft_sim->setAnalysisParm` when the metadata marks them as settable ([Source: src/spicelib/parser/inpdoopt.c#L44-L68]).

## Error handling {#errors}

Unknown option keywords append `" Error: unknown option - ignored\n"` to the card error string and print to `stderr` ([Source: src/spicelib/parser/inpdoopt.c#L71-L75]).

## Cross-reference {#cross-ref}

Tolerance and method semantics are documented in [chapter 18](../18_options_and_tolerances/README.md).
