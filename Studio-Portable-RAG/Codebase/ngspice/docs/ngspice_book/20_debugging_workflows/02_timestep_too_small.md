---
title: "Timestep too small"
chapter: "20_debugging_workflows"
section: "02_timestep_too_small"
section_number: "20.2"
topic: "02_timestep_too_small"
mission_primary: "circuit_design_validation"
mission_secondary: []
related_files:
  - "src/spicelib/analysis/dctran.c"
related_chapters:
  - "../05_numerical_integration/06_timestep_control_law.md"
domain_concepts:
  - "tran_timestep_debug"
canonical_chain_tags:
  - "transient_step_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 10
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Timestep too small {#timestep-too-small}

## Breakpoint floor {#breakpoint-floor}

`DCtran` derives `CKTminBreak` from `CKTdelmin` or `CKTmaxStep` when unset, preventing the integrator from subdividing below a meaningful resolution ([Source: src/spicelib/analysis/dctran.c#L146-L151], [Source: src/spicelib/analysis/dctran.c#L489-L493]).

## Symptom {#symptom}

Logs showing `ckt_min_break` alongside `brk_pt` indicate the solver is pinned against breakpoint quantization—often due to stiff events or unrealistic `reltol` ([Source: src/spicelib/analysis/dctran.c#L615-L621]).

## Mitigations {#mitigations}

- Relax `trtol` / tighten model limiting.
- Add realistic parasitics to remove ideal discontinuities.
- Switch integration method (`CKTintegrateMethod`, [Source: ../18_options_and_tolerances/05_method_options_trap_gear.md]).
