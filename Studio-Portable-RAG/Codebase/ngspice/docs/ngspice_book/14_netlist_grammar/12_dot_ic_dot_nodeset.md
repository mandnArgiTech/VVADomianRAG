---
title: ".ic and .nodeset"
chapter: "14_netlist_grammar"
section: "12_dot_ic_dot_nodeset"
section_number: "14.12"
topic: "12_dot_ic_dot_nodeset"
mission_primary: "circuit_design_validation"
mission_secondary: ["kernel_reimplementation"]
related_files:
  - "src/spicelib/parser/inp2dot.c"
related_chapters:
  - "../05_numerical_integration/README.md"
  - "../20_debugging_workflows/09_initial_conditions_misuse.md"
domain_concepts:
  - "initial_guess"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 9
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# .ic and .nodeset {#dot-ic-dot-nodeset}

## Parser visibility {#parser}

In `INP2dot`, both `.nodeset` and `.ic` branches currently `goto quit` without constructing an analysis job—their effect is applied through other initialization paths in the input system ([Source: src/spicelib/parser/inp2dot.c#L662-L663], [Source: src/spicelib/parser/inp2dot.c#L676-L677]).

## Conceptual difference {#conceptual}

- **`.ic`** — declares initial capacitor voltages / inductor currents for transient (`UIC` flows) and can influence the first NR guess.
- **`.nodeset`** — supplies **suggested node voltages** to bias Newton without forcing a true physical initial state.

## Debugging tie-in {#debugging}

Misapplied `.ic` is a frequent source of “correct DC, wrong transient” reports; see [chapter 20 §9](../20_debugging_workflows/09_initial_conditions_misuse.md).
