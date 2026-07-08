---
title: "Typical AC workflow"
chapter: "19_circuit_design_patterns"
section: "03_typical_ac_workflow"
section_number: "19.3"
topic: "03_typical_ac_workflow"
mission_primary: "circuit_design_validation"
mission_secondary: []
related_files:
  - "src/spicelib/parser/inp2dot.c"
  - "src/frontend/runcoms.c"
related_chapters:
  - "../03_analysis_drivers/04_ac_small_signal_acan.md"
domain_concepts:
  - "ac_workflow"
canonical_chain_tags:
  - "ac_analysis_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 9
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Typical AC workflow {#typical-ac-workflow}

## Sweep definition {#sweep}

`dot_ac` accepts `DEC`, `OCT`, or `LIN` followed by point count and frequency bounds ([Source: src/spicelib/parser/inp2dot.c#L186-L203]).

## Execution {#execution}

`com_ac` → `dosim("ac", wl)` reuses the same driver path as deck-scheduled AC jobs ([Source: src/frontend/runcoms.c#L136-L140]).

## Result handling {#results}

AC vectors are complex (`VF_COMPLEX`); use `mag`/`ph` nutmeg functions or export raw for Python ([Source: src/include/ngspice/dvec.h#L10-L11]).
