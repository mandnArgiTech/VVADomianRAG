---
title: "Writing a new regression test"
chapter: "21_validation_with_regression_suite"
section: "05_writing_a_new_regression_test"
section_number: "21.5"
topic: "writing_a_new_regression_test"
mission_primary: "circuit_design_validation"
mission_secondary: []
related_files:
  - "tests/README"
related_chapters:
  - "../21_validation_with_regression_suite/01_regression_suite_organization.md"
domain_concepts:
  - "new_regression_test"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "ngspice core developer"
estimated_reading_minutes: 8
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Writing a new regression test {#writing-a-new-regression-test}

## Clone an existing sibling {#clone}

`tests/README` instructs contributors to copy a nearby test and adapt it, then hook the script into `Makefile.am` and run `make check` ([Source: tests/README#L24-L28]).

## Produce a stable `.out` {#stable-out}

1. Run reference ngspice on the `.cir` with the same version you intend to support.
2. Trim incidental platform noise if needed, but prefer adjusting the netlist (fewer prints) over weakening global filters.
3. Store the `.out` next to the `.cir` so `check.sh` can locate both via basename ([Source: tests/bin/check.sh#L22-L23]).

## Makefile wiring {#makefile}

Add the `*.cir` target to the appropriate `TESTS` or custom rule in the subdirectory’s `Makefile.am`, mirroring neighboring entries. Re-run `automake` if you are modifying build templates in a maintainer workflow.

## Book hygiene {#hygiene}

If the test documents a kernel invariant, cross-link the scenario from the relevant chapter (convergence, device, or analysis) so future readers know why it exists.
