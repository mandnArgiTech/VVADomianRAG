---
title: "Convergence failure diagnosis chain"
chapter: "23_canonical_chains_reference"
section: "08_convergence_failure_diagnosis_chain"
section_number: "23.8"
topic: "convergence_failure_diagnosis_chain"
mission_primary: "circuit_design_validation"
mission_secondary: ["kernel_reimplementation"]
related_files:
  - "src/include/ngspice/iferrmsg.h"
  - "src/spicelib/analysis/dcop.c"
  - "src/spicelib/analysis/dctran.c"
  - "src/frontend/runcoms.c"
related_chapters:
  - "../04_convergence_aids/01_convergence_aid_ladder.md"
  - "../20_debugging_workflows/01_dc_op_no_convergence.md"
domain_concepts:
  - "convergence_diagnosis"
canonical_chain_tags:
  - "convergence_failure_diagnosis_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 8
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Convergence failure diagnosis chain {#convergence-failure-diagnosis-chain}

## Summary {#summary}

When the Newton loop or transient driver aborts, the simulator returns structured error codes (`E_*`) and optional `errMsg` / `errRtn` strings ([Source: src/include/ngspice/iferrmsg.h#L15-L56]). The interactive/batch driver `dosim` in `runcoms.c` surfaces abort status to the user and tears down raw-file handles before optional `.measure` post-processing ([Source: src/frontend/runcoms.c#L330-L361]).

## Stages {#stages}

`error_message_emit` → `user_remediation_options` ([Source: rag_index.json]).

## Canonical members {#members}

`src/include/ngspice/iferrmsg.h`, `src/spicelib/analysis/dcop.c`, `src/spicelib/analysis/dctran.c`, `src/frontend/runcoms.c`

## Deep dives {#deep-dives}

- [Convergence aids](../04_convergence_aids/01_convergence_aid_ladder.md)
- [DC non-convergence workflow](../20_debugging_workflows/01_dc_op_no_convergence.md)
