---
title: "Parametric sweep idioms"
chapter: "19_circuit_design_patterns"
section: "04_parametric_sweep_idioms"
section_number: "19.4"
topic: "04_parametric_sweep_idioms"
mission_primary: "circuit_design_validation"
mission_secondary: []
related_files:
  - "src/spicelib/parser/inp2dot.c"
related_chapters:
  - "../15_parser_and_expansion/04_parameter_substitution_numparam.md"
domain_concepts:
  - "parametric_sweep"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 9
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Parametric sweep idioms {#parametric-sweep-idioms}

## Built-in `.dc` {#built-in-dc}

`dot_dc` parses one- or two-source sweeps (`name`, `start`, `stop`, `step`) and registers them on the DC analysis job ([Source: src/spicelib/parser/inp2dot.c#L255-L284], [Source: src/spicelib/parser/inp2dot.c#L684-L686]).

## Outer loops {#outer-loops}

For arbitrary parameters, combine `.param` + `nupa_eval` substitution with repeated `run` inside `.control`, or drive ngspice via the shared API ([Source: ../01_architecture_overview/05_shared_library_mode.md]).

## Regression tip {#regression}

Capture one `.raw` per corner and diff against golden outputs using `tests/bin/check.sh` philosophy ([Source: ../21_validation_with_regression_suite/02_running_regression_tests.md]).
