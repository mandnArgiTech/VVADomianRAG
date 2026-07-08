---
title: "Numerical integration for transient"
chapter: "00_foundations"
section: "05_numerical_integration_for_transient"
section_number: "0.5"
topic: "05_numerical_integration_for_transient"
mission_primary: "kernel_reimplementation"
mission_secondary: ["circuit_design_validation"]
related_files:
  - "src/maths/ni/niinteg.c"
  - "src/include/ngspice/cktdefs.h"
  - "src/spicelib/devices/cktinit.c"
related_chapters:
  - "../05_numerical_integration/01_trapezoidal_integration.md"
  - "../05_numerical_integration/02_gear_method_orders_2_to_6.md"
  - "../03_analysis_drivers/03_transient_dctran.md"
domain_concepts:
  - "numerical_integration"
canonical_chain_tags:
  - "transient_step_chain"
numerical_invariants_introduced: []
glossary_terms_introduced:
  - "NIintegrate"
audience:
  - "NodalAI reimplementer"
  - "advanced circuit designer"
estimated_reading_minutes: 10
last_updated_from_source_at: "2026-04-09T03:39:07.069653+00:00"
---

# Numerical integration for transient {#numerical-integration-for-transient}

## Overview {#overview}

Transient analysis treats energy-storage elements (capacitors, inductors) as differential equations discretized in time. ngspice stores the integration method and order on `CKTcircuit`: `CKTintegrateMethod` is either `TRAPEZOIDAL` or `GEAR`, and `CKTorder` / `CKTmaxOrder` bound the BDF/trap orders actually used ([Source: src/include/ngspice/cktdefs.h#L101-L107]). At setup, `CKTinit` defaults to trapezoidal integration with order 1 and max order 2 ([Source: src/spicelib/devices/cktinit.c#L63-L65]).

The shared routine `NIintegrate` maps stored charge histories into equivalent conductance `*geq` and current `*ceq` pairs used during stamping ([Source: src/maths/ni/niinteg.c#L17-L79]).

<!-- source: src/maths/ni/niinteg.c -->
<!-- source: src/include/ngspice/cktdefs.h -->
<!-- source: src/spicelib/devices/cktinit.c -->

## What This Section Does {#what-it-does}

Provides the bridge between *continuous-time* device physics and the *discrete* Newton solves executed at each time step. Chapter 5 goes deeper; here we focus on the function that all capacitor models ultimately rely on.

## `NIintegrate` Mechanics {#niintegrate}

`NIintegrate(ckt, geq, ceq, cap, qcap)` switches on `ckt->CKTintegrateMethod`:

- **Trapezoidal** — Orders 1 and 2 combine `CKTstate0[qcap]` and `CKTstate1[qcap]` with coefficients `CKTag[]` ([Source: src/maths/ni/niinteg.c#L25-L40]).
- **Gear (BDF family)** — Orders 1 through 6 accumulate contributions from `CKTstate1`…`CKTstate6` with the corresponding `CKTag[k]` weights ([Source: src/maths/ni/niinteg.c#L42-L64]).

It then forms the companion values

\[
*ceq = \text{ccap} - \texttt{CKTag[0]} \cdot q, \quad *geq = \texttt{CKTag[0]} \cdot cap
\]

([Source: src/maths/ni/niinteg.c#L77-L78]), which is the standard replacement of a capacitor with a conductance in parallel with a history current source for the current Newton linearization.

## Failure Modes {#failure-modes}

Unsupported integration order returns `E_ORDER`; unknown method returns `E_METHOD` ([Source: src/maths/ni/niinteg.c#L36-L40, L66-L75]).

## Source Files {#source-files}

- **`src/maths/ni/niinteg.c`** — `NIintegrate`.
- **`src/include/ngspice/cktdefs.h`** — integration enums and state vectors.
- **`src/spicelib/devices/cktinit.c`** — default method/order.

## Related Chapters {#related-chapters}

- [Trapezoidal integration](../05_numerical_integration/01_trapezoidal_integration.md)
- [Gear method](../05_numerical_integration/02_gear_method_orders_2_to_6.md)
- [Transient driver](../03_analysis_drivers/03_transient_dctran.md)

## Canonical Chains {#canonical-chains}

- `transient_step_chain` — predictor, integration, NR, truncation (see `rag_index.json`).

## Glossary {#glossary}

- **NIintegrate** — ngspice helper that converts history states to `geq`/`ceq`. See [Numerical kernel terms](../24_glossary/01_numerical_kernel_terms.md#numerical-kernel-terms).
