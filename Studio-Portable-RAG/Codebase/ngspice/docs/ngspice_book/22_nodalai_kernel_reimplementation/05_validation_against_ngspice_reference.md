---
title: "Validation against ngspice reference"
chapter: "22_nodalai_kernel_reimplementation"
section: "05_validation_against_ngspice_reference"
section_number: "22.5"
topic: "validation_against_ngspice_reference"
mission_primary: "kernel_reimplementation"
mission_secondary: ["circuit_design_validation"]
related_files:
  - "tests/bin/check.sh"
related_chapters:
  - "../21_validation_with_regression_suite/02_running_regression_tests.md"
  - "../21_validation_with_regression_suite/03_reading_reference_outputs.md"
domain_concepts:
  - "regression_validation"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 9
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Validation against ngspice reference {#validation-against-ngspice-reference}

## Golden outputs {#golden}

Upstream ngspice ships paired `*.cir` / `*.out` files. The Automake harness runs `ngspice --batch` and `diff`s filtered logs against the reference ([Source: tests/bin/check.sh#L20-L47]).

## What to compare first {#compare-first}

1. **DC node voltages** and branch currents (low noise).
2. **Transient waveforms** at a coarse time grid after matching DCOP.
3. **AC magnitudes/phases** once linearization matches.

## Tolerance policy {#tolerance}

Match ngspice’s **option set** (`RELTOL`, `VNTOL`, integration method) before declaring mismatch; many “kernel bugs” are configuration drift ([Source: ../18_options_and_tolerances/01_options_overview.md]).
