---
title: "Oscillation in simulation (not in the circuit)"
chapter: "20_debugging_workflows"
section: "06_oscillation_in_simulation_not_circuit"
section_number: "20.6"
topic: "06_oscillation_in_simulation_not_circuit"
mission_primary: "circuit_design_validation"
mission_secondary: []
related_files:
  - "src/maths/ni/niinteg.c"
  - "src/spicelib/analysis/dctran.c"
related_chapters:
  - "../05_numerical_integration/01_trapezoidal_integration.md"
domain_concepts:
  - "numerical_oscillation"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 10
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Oscillation in simulation (not in the circuit) {#oscillation-in-simulation-not-circuit}

## Numerical ringing {#ringing}

Trapezoidal integration can exhibit **Nyquist-limit ringing** even when the physical circuit is damped; `NIintegrate`’s trapezoidal branch uses two-point history ([Source: src/maths/ni/niinteg.c#L25-L35]).

## Mitigation {#mitigation}

- Switch to Gear or reduce `maxstep`.
- Insert small parasitic RC to regularize nodes.
- Compare with `reltol` tightened/loosened to see if the artifact is LTE-driven ([Source: ../05_numerical_integration/06_timestep_control_law.md]).

## Breakpoint interplay {#breakpoint}

`DCtran` enforces minimum spacing near breakpoints; mis-tuned `CKTminBreak` can exacerbate chatter ([Source: src/spicelib/analysis/dctran.c#L615-L621]).
