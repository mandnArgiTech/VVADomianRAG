---
title: "Method options (trapezoidal vs Gear)"
chapter: "18_options_and_tolerances"
section: "05_method_options_trap_gear"
section_number: "18.5"
topic: "05_method_options_trap_gear"
mission_primary: "circuit_design_validation"
mission_secondary: ["kernel_reimplementation"]
related_files:
  - "src/include/ngspice/cktdefs.h"
  - "src/maths/ni/niinteg.c"
related_chapters:
  - "../05_numerical_integration/README.md"
domain_concepts:
  - "integration_method"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 10
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Method options (trapezoidal vs Gear) {#method-options-trap-gear}

## Selector {#selector}

`CKTintegrateMethod` stores the active quadrature rule; companion fields (`CKTorder`, `CKTag[]`) supply multistep coefficients ([Source: src/include/ngspice/cktdefs.h#L103]).

## Implementation split {#implementation}

`NIintegrate` switches on `TRAPEZOIDAL` vs `GEAR`, updating capacitor companion models differently per order ([Source: src/maths/ni/niinteg.c#L23-L44]).

## Practice {#practice}

- Trapezoidal is default and energy-conserving in many RC networks but can ring.
- Gear provides stronger damping at the cost of more history storage—see [chapter 5](../05_numerical_integration/README.md).
