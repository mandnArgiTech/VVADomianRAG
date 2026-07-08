---
title: "Unrealistic results"
chapter: "20_debugging_workflows"
section: "05_unrealistic_results"
section_number: "20.5"
topic: "05_unrealistic_results"
mission_primary: "circuit_design_validation"
mission_secondary: []
related_files:
  - "src/spicelib/parser/inpdoopt.c"
related_chapters:
  - "../18_options_and_tolerances/08_options_in_practice.md"
domain_concepts:
  - "sanity_checking"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 9
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Unrealistic results {#unrealistic-results}

## Silent misconfiguration {#silent-misconfiguration}

Typos in `.options` produce `"unknown option - ignored"` warnings that users may miss—always inspect stderr ([Source: src/spicelib/parser/inpdoopt.c#L71-L75]).

## Sanity checklist {#checklist}

1. Confirm temperature (`CKTtemp`) matches the intended corner ([Source: src/include/ngspice/cktdefs.h#L93]).
2. Verify model cards (`inpdomod`) reference existing levels.
3. Cross-validate a simplified reference netlist with hand calculations.

## Regression guard {#regression}

Lock golden `.out` files via `make check` to catch accidental option drift ([Source: ../21_validation_with_regression_suite/01_regression_suite_organization.md]).
