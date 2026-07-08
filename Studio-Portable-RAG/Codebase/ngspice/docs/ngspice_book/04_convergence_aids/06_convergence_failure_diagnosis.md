---
title: "Convergence failure diagnosis"
chapter: "04_convergence_aids"
section: "06_convergence_failure_diagnosis"
section_number: "4.6"
topic: "06_convergence_failure_diagnosis"
mission_primary: "circuit_design_validation"
mission_secondary: ["kernel_reimplementation"]
related_files:
  - "src/spicelib/analysis/dcop.c"
  - "src/maths/ni/niconv.c"
related_chapters:
  - "../20_debugging_workflows/README.md"
  - "../18_options_and_tolerances/README.md"
domain_concepts:
  - "convergence_failure"
canonical_chain_tags:
  - "convergence_failure_diagnosis_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 9
last_updated_from_source_at: "2026-04-09T03:39:07.072860+00:00"
---

# Convergence failure diagnosis {#convergence-failure-diagnosis}

## Overview {#overview}

When `DCop` fails, ngspice prints a banner and calls `CKTncDump` to emit the last node voltages for inspection ([Source: src/spicelib/analysis/dcop.c#L86-L88]). During Newton, `NIconvTest` records `CKTtroubleNode` for the first row violating the mixed `RELTOL`/`VNTOL`/`ABSTOL` test ([Source: src/maths/ni/niconv.c#L49-L63]).

<!-- source: src/spicelib/analysis/dcop.c -->
<!-- source: src/maths/ni/niconv.c -->

## Practical Checklist {#checklist}

1. **Raise aids** — Increase `gminsteps` / `srcsteps` or enable `noopiter` to skip straight Newton ([Source: src/spicelib/analysis/cktop.c#L33-L45], [Source: src/spicelib/analysis/cktsopt.c#L230]).
2. **Relax/tighten tolerances** — `.options reltol vntol abstol` feed the same structs `NIconvTest` reads ([Source: src/spicelib/analysis/cktsopt.c#L233-L237]).
3. **Inspect trouble node** — Aligns with `CKTtroubleNode` bookkeeping in `niconv.c`.

## Source Files {#source-files}

- **`src/spicelib/analysis/dcop.c`**
- **`src/maths/ni/niconv.c`**

## Related Chapters {#related-chapters}

- [Debugging workflows](../20_debugging_workflows/README.md)
- [Options & tolerances](../18_options_and_tolerances/README.md)

## Canonical Chains {#canonical-chains}

- `convergence_failure_diagnosis_chain`
