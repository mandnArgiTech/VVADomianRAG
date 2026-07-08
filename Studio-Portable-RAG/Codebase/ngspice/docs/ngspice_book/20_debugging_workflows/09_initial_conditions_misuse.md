---
title: "Initial conditions misuse"
chapter: "20_debugging_workflows"
section: "09_initial_conditions_misuse"
section_number: "20.9"
topic: "09_initial_conditions_misuse"
mission_primary: "circuit_design_validation"
mission_secondary: []
related_files:
  - "src/spicelib/parser/inp2dot.c"
related_chapters:
  - "../14_netlist_grammar/12_dot_ic_dot_nodeset.md"
domain_concepts:
  - "uic_pitfalls"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 9
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Initial conditions misuse {#initial-conditions-misuse}

## Parser surface {#parser-surface}

`INP2dot` acknowledges `.ic` lines but does not attach analysis jobs—the actual initialization is handled elsewhere during setup ([Source: src/spicelib/parser/inp2dot.c#L676-L677]).

## UIC interactions {#uic}

`dot_tran` records `uic` when present, skipping the usual DC equilibrium for capacitor voltages ([Source: src/spicelib/parser/inp2dot.c#L386-L393]).

## Failure modes {#failure-modes}

- Inconsistent `.ic` vs resistor divider steady state → large inrush currents.
- Mixing `.nodeset` guesses with `UIC` without understanding which wins.

## Fix {#fix}

Remove `UIC` temporarily, verify DCOP, then reintroduce carefully while monitoring branch currents.
