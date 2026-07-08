---
title: "DC operating point (DCop)"
chapter: "03_analysis_drivers"
section: "01_dc_operating_point_dcop"
section_number: "3.1"
topic: "01_dc_operating_point_dcop"
mission_primary: "kernel_reimplementation"
mission_secondary: ["circuit_design_validation"]
related_files:
  - "src/spicelib/analysis/dcop.c"
  - "src/spicelib/analysis/cktop.c"
related_chapters:
  - "../02_numerical_kernel_core/02_newton_raphson_iteration_niiter.md"
  - "../23_canonical_chains_reference/01_dc_operating_point_chain.md"
domain_concepts:
  - "dc_operating_point"
canonical_chain_tags:
  - "dc_operating_point_chain"
numerical_invariants_introduced:
  - "newton_raphson_iteration"
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 10
last_updated_from_source_at: "2026-04-09T03:39:07.072860+00:00"
---

# DC operating point (DCop) {#dc-operating-point-dcop}

## Overview {#overview}

`DCop` prepares output metadata, optionally initializes SOA checks, then solves the nonlinear DC equations by calling `CKTop` with `MODEINITJCT` / `MODEINITFLOAT` masks and the `CKTdcMaxIter` budget ([Source: src/spicelib/analysis/dcop.c#L81-L84]). XSPICE builds may route through `EVTop` when event-driven instances exist ([Source: src/spicelib/analysis/dcop.c#L67-L80]).

`CKTop` itself first attempts `NIiter`; on failure it walks the convergence ladder (GMIN stepping, source stepping) ([Source: src/spicelib/analysis/cktop.c#L33-L72]).

<!-- source: src/spicelib/analysis/dcop.c -->
<!-- source: src/spicelib/analysis/cktop.c -->

## Algorithm {#algorithm}

1. Name nodes / begin plot ([Source: src/spicelib/analysis/dcop.c#L51-L59]).
2. `CKTsoaInit` when SOA checking enabled ([Source: src/spicelib/analysis/dcop.c#L61-L63]).
3. Call `CKTop(..., ckt->CKTdcMaxIter)` for classical SPICE path ([Source: src/spicelib/analysis/dcop.c#L81-L84]).
4. On non-zero return, dump non-convergence diagnostics (`CKTncDump`, [Source: src/spicelib/analysis/dcop.c#L86-L88]).

## Source Files {#source-files}

- **`src/spicelib/analysis/dcop.c`**
- **`src/spicelib/analysis/cktop.c`**

## Related Chapters {#related-chapters}

- [NIiter](../02_numerical_kernel_core/02_newton_raphson_iteration_niiter.md)
- [Convergence aids](../04_convergence_aids/01_convergence_aid_ladder.md)
- [DC OP chain](../23_canonical_chains_reference/01_dc_operating_point_chain.md)

## Canonical Chains {#canonical-chains}

- `dc_operating_point_chain`
