---
title: "Convergence aid directive sequence"
chapter: "20_debugging_workflows"
section: "07_convergence_aid_directive_sequence"
section_number: "20.7"
topic: "07_convergence_aid_directive_sequence"
mission_primary: "circuit_design_validation"
mission_secondary: []
related_files:
  - "src/spicelib/analysis/cktop.c"
related_chapters:
  - "../04_convergence_aids/01_convergence_aid_ladder.md"
domain_concepts:
  - "convergence_sequence"
canonical_chain_tags:
  - "convergence_aid_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 9
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Convergence aid directive sequence {#convergence-aid-directive-sequence}

## Automatic ordering {#ordering}

`CKTop` always attempts plain `NIiter` first unless `CKTnoOpIter` short-circuits to gmin stepping ([Source: src/spicelib/analysis/cktop.c#L33-L45], [Source: src/include/ngspice/cktdefs.h#L233-L235]).

## Ladder {#ladder}

Failure triggers gmin variants, then source stepping, matching the canonical convergence-aid chain ([Source: src/spicelib/analysis/cktop.c#L48-L72]).

## Netlist hints {#hints}

There is no per-card “sequence” beyond options: use `.options ITL… GMIN…` to tune the same code paths the kernel already executes.
