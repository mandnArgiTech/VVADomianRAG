---
title: "Monte Carlo idioms"
chapter: "19_circuit_design_patterns"
section: "05_monte_carlo_idioms"
section_number: "19.5"
topic: "05_monte_carlo_idioms"
mission_primary: "circuit_design_validation"
mission_secondary: []
related_files:
  - "src/frontend/numparam/numpaif.h"
related_chapters:
  - "../15_parser_and_expansion/04_parameter_substitution_numparam.md"
domain_concepts:
  - "monte_carlo"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 8
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Monte Carlo idioms {#monte-carlo-idioms}

## ngspice baseline {#ngspice-baseline}

Core ngspice does not ship a single `.mc` card; Monte Carlo flows are built by **outer scripts** that rewrite `.param` lines or call `ngSpice_Circ` repeatedly with perturbed values ([Source: src/frontend/numparam/numpaif.h#L18-L21]).

## Pattern {#pattern}

1. Express statistical parameters as `.param` equations.
2. Use Python/shell to substitute draws before each run.
3. Aggregate `.measure` results post-simulation ([Source: ../17_output_and_results/04_measure_extraction_idioms.md]).

## Kernel note {#kernel-note}

Ensure each trial starts from a clean `CKTcircuit` (new process or `reset`) so RNG noise does not correlate with stale state.
