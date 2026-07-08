---
title: "Backward Euler"
chapter: "05_numerical_integration"
section: "03_backward_euler"
section_number: "5.3"
topic: "03_backward_euler"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/maths/ni/niinteg.c"
  - "src/spicelib/analysis/dctran.c"
related_chapters:
  - "01_trapezoidal_integration.md"
domain_concepts:
  - "numerical_integration"
canonical_chain_tags:
  - "transient_step_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 6
last_updated_from_source_at: "2026-04-09T03:39:07.069653+00:00"
---

# Backward Euler {#backward-euler}

## Overview {#overview}

Backward Euler corresponds to integration **order 1** inside `NIintegrate`: for trapezoidal mode the `CKTorder == 1` branch uses only `CKTag[0]` and `CKTag[1]` with `CKTstate0` / `CKTstate1` ([Source: src/maths/ni/niinteg.c#L26-L30]). For Gear mode, order 1 collapses the switch to the final two-term accumulation ([Source: src/maths/ni/niinteg.c#L61-L63]).

`DCtran` explicitly resets `CKTorder = 1` after a failed Newton step or breakpoint rewind ([Source: src/spicelib/analysis/dctran.c#L810, L825]).

<!-- source: src/maths/ni/niinteg.c -->
<!-- source: src/spicelib/analysis/dctran.c -->

## Source Files {#source-files}

- **`src/maths/ni/niinteg.c`**
- **`src/spicelib/analysis/dctran.c`**
