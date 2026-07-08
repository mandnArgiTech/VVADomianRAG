---
title: "Running regression tests"
chapter: "21_validation_with_regression_suite"
section: "02_running_regression_tests"
section_number: "21.2"
topic: "running_regression_tests"
mission_primary: "circuit_design_validation"
mission_secondary: []
related_files:
  - "tests/Makefile.am"
  - "tests/bin/check.sh"
related_chapters:
  - "../21_validation_with_regression_suite/01_regression_suite_organization.md"
domain_concepts:
  - "make_check"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "ngspice core developer"
estimated_reading_minutes: 8
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Running regression tests {#running-regression-tests}

## Automake entry point {#automake}

`TESTS_ENVIRONMENT` wires `make check` to invoke `tests/bin/check.sh` with the built `ngspice` binary as the first argument and each scheduled test as the second ([Source: tests/Makefile.am#L44-L45]).

## Local workflow {#workflow}

1. Configure and build the tree per upstream instructions (`tests/README` notes a plain `./configure` baseline).
2. Run `make check` from the build directory; failing tests leave `*.test` artifacts next to the reference for inspection ([Source: tests/bin/check.sh#L41-L48]).

## Platform branches {#platforms}

`check.sh` selects `diff` flags and pre-processing `sed` pipelines based on `uname` (Windows vs Linux/macOS vs SunOS/OpenBSD) ([Source: tests/bin/check.sh#L27-L59]). When triaging CI-only failures, reproduce the host class or adjust filters cautiously—over-broad `egrep -v` patterns can hide real regressions.
