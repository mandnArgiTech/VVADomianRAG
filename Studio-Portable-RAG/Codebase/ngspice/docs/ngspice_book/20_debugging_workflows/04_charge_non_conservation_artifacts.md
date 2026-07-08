---
title: "Charge non-conservation artifacts"
chapter: "20_debugging_workflows"
section: "04_charge_non_conservation_artifacts"
section_number: "20.4"
topic: "04_charge_non_conservation_artifacts"
mission_primary: "circuit_design_validation"
mission_secondary: []
related_files:
  - "src/maths/ni/niinteg.c"
related_chapters:
  - "../05_numerical_integration/04_charge_conserving_capacitor_stamps.md"
domain_concepts:
  - "charge_conservation"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 10
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Charge non-conservation artifacts {#charge-non-conservation-artifacts}

## Integration path {#integration-path}

`NIintegrate` builds companion models from stored charge history (`CKTstate*`) for both trapezoidal and Gear branches ([Source: src/maths/ni/niinteg.c#L23-L44]).

## Symptoms {#symptoms}

Glitches in switched-capacitor or charge-pump simulations often trace to **model capacitance implementations** that are not charge-defined, or to overly aggressive `CHGTOL`.

## Debug steps {#debug-steps}

1. Verify capacitor models use charge formulations in transient.
2. Compare `trap` vs `gear` integration.
3. Tighten `CHGTOL` only after confirming limiting is stable ([Source: src/include/ngspice/cktdefs.h#L202]).
