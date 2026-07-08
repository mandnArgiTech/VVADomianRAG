---
title: "Convergence test anatomy"
chapter: "02_numerical_kernel_core"
section: "03_convergence_test_anatomy"
section_number: "2.3"
topic: "03_convergence_test_anatomy"
mission_primary: "kernel_reimplementation"
mission_secondary: ["circuit_design_validation"]
related_files:
  - "src/maths/ni/niconv.c"
  - "src/spicelib/analysis/cktop.c"
  - "src/include/ngspice/cktdefs.h"
related_chapters:
  - "02_newton_raphson_iteration_niiter.md"
  - "../18_options_and_tolerances/02_tolerance_options_reltol_abstol_vntol_chgtol.md"
domain_concepts:
  - "convergence_test"
canonical_chain_tags:
  - "dc_operating_point_chain"
numerical_invariants_introduced:
  - "convergence_test"
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
  - "advanced circuit designer"
estimated_reading_minutes: 10
last_updated_from_source_at: "2026-04-09T03:39:07.069477+00:00"
---

# Convergence test anatomy {#convergence-test-anatomy}

## Overview {#overview}

`NIconvTest` implements the classical SPICE per-row check: for each MNA unknown, compare the latest solution (`CKTrhs`) with the previous iterate (`CKTrhsOld`). Voltages use `RELTOL` + `VNTOL`; all other rows use `RELTOL` + `ABSTOL` ([Source: src/maths/ni/niconv.c#L37-L64]).

When compiled with `NEWCONV`, an additional device-specific pass runs via `CKTconvTest` ([Source: src/maths/ni/niconv.c#L68-L74]).

<!-- source: src/maths/ni/niconv.c -->
<!-- source: src/spicelib/analysis/cktop.c -->

## What This Module Does {#what-it-does}

Returns `0` if every row satisfies the tolerance inequality, otherwise `1` and records `CKTtroubleNode` for diagnostics ([Source: src/maths/ni/niconv.c#L49-L63]).

## Algebraic Test {#algebra}

For row \(i\) with node `node`:

- If `node->type == SP_VOLTAGE`:

\[
|v_{\text{new}} - v_{\text{old}}| \le \texttt{CKTreltol} \cdot \max(|v_{\text{old}}|,|v_{\text{new}}|) + \texttt{CKTvoltTol}
\]

- Else:

\[
|x_{\text{new}} - x_{\text{old}}| \le \texttt{CKTreltol} \cdot \max(|x_{\text{old}}|,|x_{\text{new}}|) + \texttt{CKTabstol}
\]

([Source: src/maths/ni/niconv.c#L41-L56])

## Device Hook Path {#cktconvtest}

`CKTconvTest` walks `DEVices[i]->DEVconvTest` just like `CKTload` walks `DEVload` ([Source: src/spicelib/analysis/cktop.c#L98-L111]). Builds that include `NEWCONV` layer this atop the algebraic test.

## Numerical Invariants {#invariants}

| Invariant | Specification | Source |
|-----------|---------------|--------|
| Voltage tolerance mix | `RELTOL` scaling + `CKTvoltTol` | [Source: src/maths/ni/niconv.c#L41-L44] |
| Current/other tolerance mix | `RELTOL` scaling + `CKTabstol` | [Source: src/maths/ni/niconv.c#L53-L56] |
| Trouble metadata | First failing row stored in `CKTtroubleNode` | [Source: src/maths/ni/niconv.c#L49-L50] |

## Source Files {#source-files}

- **`src/maths/ni/niconv.c`** — `NIconvTest`.
- **`src/spicelib/analysis/cktop.c`** — `CKTconvTest` driver.
- **`src/include/ngspice/cktdefs.h`** — tolerance fields on `CKTcircuit`.

## Related Chapters {#related-chapters}

- [NIiter](02_newton_raphson_iteration_niiter.md)
- [Tolerance options](../18_options_and_tolerances/02_tolerance_options_reltol_abstol_vntol_chgtol.md)

## Canonical Chains {#canonical-chains}

- `dc_operating_point_chain` — convergence stage after each NR solve.
