---
title: "Typical transient workflow"
chapter: "19_circuit_design_patterns"
section: "02_typical_transient_workflow"
section_number: "19.2"
topic: "02_typical_transient_workflow"
mission_primary: "circuit_design_validation"
mission_secondary: []
related_files:
  - "src/spicelib/parser/inp2dot.c"
  - "src/frontend/runcoms.c"
related_chapters:
  - "../03_analysis_drivers/03_transient_dctran.md"
domain_concepts:
  - "tran_workflow"
canonical_chain_tags:
  - "transient_step_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 9
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Typical transient workflow {#typical-transient-workflow}

## Deck setup {#deck-setup}

`.tran Tstep Tstop [Tstart [Tmax]] [UIC]` is parsed in `dot_tran`, which fills `tstep`, `tstop`, optional `tstart`/`tmax`, and the `uic` flag ([Source: src/spicelib/parser/inp2dot.c#L363-L394]).

## Command-line {#command-line}

`tran` in nutmeg maps to `dosim("tran", wl)` ([Source: src/frontend/runcoms.c#L150-L154]).

## Checklist {#checklist}

1. Confirm DCOP converges (`op`).
2. Choose integration method / `maxstep` consistent with fastest pole.
3. Save waveforms with `write` for regression diffing ([Source: ../17_output_and_results/02_raw_file_format_spec.md]).
