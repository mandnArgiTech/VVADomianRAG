---
title: "Options and tolerances terms"
chapter: "24_glossary"
section: "04_options_and_tolerances_terms"
section_number: "24.4"
topic: "04_options_and_tolerances_terms"
mission_primary: "circuit_design_validation"
mission_secondary: ["kernel_reimplementation"]
related_files:
  - "src/include/ngspice/cktdefs.h"
  - "src/spicelib/parser/inpdoopt.c"
related_chapters:
  - "../18_options_and_tolerances/README.md"
domain_concepts:
  - "glossary_options"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced:
  - "RELTOL"
  - "ITL1"
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 10
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Options and tolerances terms {#options-tolerances-terms}

## `RELTOL` / `ABSTOL` / `VNTOL` / `CHGTOL` {#tolerances}

Stored as `CKTreltol`, `CKTabstol`, `CKTvoltTol`, `CKTchgtol` on `CKTcircuit` ([Source: src/include/ngspice/cktdefs.h#L198-L203]).

## `ITL1` / `ITL2` / `ITL4` {#itl}

Map to `CKTdcMaxIter`, `CKTdcTrcvMaxIter`, `CKTtranMaxIter` ([Source: src/include/ngspice/cktdefs.h#L187-L192]).

## `GMIN` {#gmin}

Minimum shunt conductance `CKTgmin` augmented by stepping helpers ([Source: src/include/ngspice/cktdefs.h#L209-L222]).

## `.options` parsing {#options-parsing}

`INPdoOpts` applies tokens through `ft_sim->setAnalysisParm` ([Source: src/spicelib/parser/inpdoopt.c#L61-L68]).

## Integration method {#integration-method}

`CKTintegrateMethod` selects trapezoidal vs Gear integration ([Source: src/include/ngspice/cktdefs.h#L103], [Source: src/maths/ni/niinteg.c#L23-L44]).
