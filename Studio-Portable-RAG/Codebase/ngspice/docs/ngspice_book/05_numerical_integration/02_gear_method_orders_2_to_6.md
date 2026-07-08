---
title: "Gear method (orders 2–6)"
chapter: "05_numerical_integration"
section: "02_gear_method_orders_2_to_6"
section_number: "5.2"
topic: "02_gear_method_orders_2_to_6"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/maths/ni/niinteg.c"
  - "src/spicelib/analysis/cktsopt.c"
related_chapters:
  - "06_timestep_control_law.md"
domain_concepts:
  - "numerical_integration"
canonical_chain_tags:
  - "transient_step_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 8
last_updated_from_source_at: "2026-04-09T03:39:07.069653+00:00"
---

# Gear method (orders 2–6) {#gear-method-orders-2-to-6}

## Overview {#overview}

For `CKTintegrateMethod == GEAR`, `NIintegrate` accumulates contributions from `CKTstate1` … `CKTstate6` depending on `CKTorder`, using weights `CKTag[k]` ([Source: src/maths/ni/niinteg.c#L42-L64]).

`.options method=gear` selects this branch ([Source: src/spicelib/analysis/cktsopt.c#L133-L137, L264]). `maxord` is clamped to `[1,6]` when parsed ([Source: src/spicelib/analysis/cktsopt.c#L115-L125, L265]).

<!-- source: src/maths/ni/niinteg.c -->
<!-- source: src/spicelib/analysis/cktsopt.c -->

## Source Files {#source-files}

- **`src/maths/ni/niinteg.c`**
- **`src/spicelib/analysis/cktsopt.c`**

## Related Chapters {#related-chapters}

- [Timestep control](06_timestep_control_law.md)
