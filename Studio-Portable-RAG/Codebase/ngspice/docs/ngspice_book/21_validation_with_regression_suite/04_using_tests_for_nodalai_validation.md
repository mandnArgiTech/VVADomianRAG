---
title: "Using tests for NodalAI validation"
chapter: "21_validation_with_regression_suite"
section: "04_using_tests_for_nodalai_validation"
section_number: "21.4"
topic: "using_tests_for_nodalai_validation"
mission_primary: "kernel_reimplementation"
mission_secondary: ["circuit_design_validation"]
related_files:
  - "tests/bin/check.sh"
related_chapters:
  - "../22_nodalai_kernel_reimplementation/05_validation_against_ngspice_reference.md"
  - "../23_canonical_chains_reference/01_dc_operating_point_chain.md"
domain_concepts:
  - "alternative_kernel_ci"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 9
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Using tests for NodalAI validation {#using-tests-for-nodalai-validation}

## Adapter strategy {#adapter}

Point `check.sh`’s `$SPICE` argument at a wrapper that:

1. Ingests the `.cir` path.
2. Runs your kernel / Python harness.
3. Emits **ngspice-compatible stdout** (or post-process your output into the filtered canonical form).

Because the harness only cares about the filtered diff ([Source: tests/bin/check.sh#L41-L47]), you can normalize formats—but do not weaken filters to hide divergence.

## Progressive coverage {#coverage}

| Phase | Suggested folders |
|-------|-------------------|
| Linear DC | `tests/resistance`, simple `regression/misc` |
| Nonlinear DC | `tests/general`, targeted diode/BJT cases |
| MOS | `tests/bsim3`, `tests/bsim4` slices |
| Transient | `tests/transient` after LTE matches |

## Tie-back to chains {#chains}

Each failing test should map to a **canonical chain** (for example DCOP → [chain 23.1](../23_canonical_chains_reference/01_dc_operating_point_chain.md)) so you know whether to instrument `NIiter`, `CKTload`, or the analysis driver.
