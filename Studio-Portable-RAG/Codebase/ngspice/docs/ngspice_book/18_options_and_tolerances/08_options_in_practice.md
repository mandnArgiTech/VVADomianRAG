---
title: "Options in practice"
chapter: "18_options_and_tolerances"
section: "08_options_in_practice"
section_number: "18.8"
topic: "08_options_in_practice"
mission_primary: "circuit_design_validation"
mission_secondary: []
related_files:
  - "src/spicelib/parser/inpdoopt.c"
  - "src/spicelib/analysis/cktop.c"
related_chapters:
  - "../20_debugging_workflows/README.md"
domain_concepts:
  - "options_recipes"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 11
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Options in practice {#options-in-practice}

## Start from defaults {#defaults}

Unknown `.options` tokens still emit warnings via `INPdoOpts`, so keep a minimal set and verify stderr in CI ([Source: src/spicelib/parser/inpdoopt.c#L71-L75]).

## Convergence stack {#convergence-stack}

When DC fails, combine **looser `RELTOL` trials** with **`CKTnumGminSteps` > 0** before raising ITL—the ladder in `CKTop` is cheaper than an infinite NR loop ([Source: src/spicelib/analysis/cktop.c#L48-L72]).

## Transient checklist {#transient-checklist}

1. Fix DCOP (`op` command) with same options.
2. Set `method` + `maxstep` consistent with LTE needs ([Source: ../05_numerical_integration/06_timestep_control_law.md]).
3. Only then tighten `RELTOL` for sign-off.
