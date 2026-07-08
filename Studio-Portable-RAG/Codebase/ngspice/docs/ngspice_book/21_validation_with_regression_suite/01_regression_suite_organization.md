---
title: "Regression suite organization"
chapter: "21_validation_with_regression_suite"
section: "01_regression_suite_organization"
section_number: "21.1"
topic: "regression_suite_organization"
mission_primary: "circuit_design_validation"
mission_secondary: ["kernel_reimplementation"]
related_files:
  - "tests/README"
  - "tests/Makefile.am"
  - "tests/regression/Makefile.am"
related_chapters:
  - "../22_nodalai_kernel_reimplementation/05_validation_against_ngspice_reference.md"
domain_concepts:
  - "regression_layout"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
  - "ngspice core developer"
estimated_reading_minutes: 10
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Regression suite organization {#regression-suite-organization}

## Top-level layout {#layout}

The `tests/` tree groups scenarios by **device family** and **analysis type** (BSIM folders, `transient/`, `regression/`, optional `xspice/`). Automake’s `SUBDIRS` list controls which buckets build by default ([Source: tests/Makefile.am#L3-L9]).

## File conventions {#files}

`tests/README` documents the pairing:

- **`*.cir`** — netlist under test.
- **`*.out`** — captured stdout/results from a reference ngspice run used as the oracle ([Source: tests/README#L11-L17]).

## Regression subtree {#regression}

`tests/regression/` further splits into `parser`, `subckt-processing`, `model`, `func`, `misc`, and `lib-processing` ([Source: tests/regression/Makefile.am#L3]). Use these when bisecting whether a failure is **frontend**, **hierarchy**, or **kernel** related.

## Relation to NodalAI {#nodalai}

Treat each passing `check.sh` pair as a **contract test** for your reimplementation: the same `.cir` should land in the same numerical basin as the checked-in `.out` after filtering ([Source: tests/bin/check.sh#L20-L47]).
