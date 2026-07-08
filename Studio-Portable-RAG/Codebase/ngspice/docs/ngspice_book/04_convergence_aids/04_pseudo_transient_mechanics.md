---
title: "Pseudo-transient and related stabilization"
chapter: "04_convergence_aids"
section: "04_pseudo_transient_mechanics"
section_number: "4.4"
topic: "04_pseudo_transient_mechanics"
mission_primary: "circuit_design_validation"
mission_secondary: ["kernel_reimplementation"]
related_files:
  - "src/spicelib/analysis/cktop.c"
  - "src/maths/ni/niiter.c"
related_chapters:
  - "01_convergence_aid_ladder.md"
  - "../03_analysis_drivers/03_transient_dctran.md"
domain_concepts:
  - "convergence_aids"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 7
last_updated_from_source_at: "2026-04-09T03:39:07.072860+00:00"
---

# Pseudo-transient and related stabilization {#pseudo-transient-mechanics}

## What ngspice Names in Code {#naming}

The on-disk DC driver `CKTop` implements **GMIN stepping** and **source stepping** after Newton fails—there is no function literally named “pseudo_transient” in `cktop.c` ([Source: src/spicelib/analysis/cktop.c#L48-L72]).

## UIC / Transient-Related Shortcut {#uic}

`NIiter` contains a specialized path for `MODETRANOP` with `MODEUIC`: it swaps RHS buffers, performs a single `CKTload`, and returns without a full Newton loop ([Source: src/maths/ni/niiter.c#L51-L59]). This supports initial-condition flows that designers sometimes combine with transient ramp strategies, but it is **not** the same algorithm as GMIN/source stepping.

## Practical Guidance {#guidance}

When literature refers to “pseudo-transient continuation,” engineers often reproduce the effect by:

- Using `.options gminsteps srcsteps` (wired in `cktsopt.c`, [Source: src/spicelib/analysis/cktsopt.c#L88-L93]),
- Or crafting a `.tran` ramp on supplies and freezing state—handled in `DCtran`, not `CKTop`.

## Source Files {#source-files}

- **`src/spicelib/analysis/cktop.c`**
- **`src/maths/ni/niiter.c`**

## Related Chapters {#related-chapters}

- [Convergence ladder](01_convergence_aid_ladder.md)
- [Transient driver](../03_analysis_drivers/03_transient_dctran.md)
