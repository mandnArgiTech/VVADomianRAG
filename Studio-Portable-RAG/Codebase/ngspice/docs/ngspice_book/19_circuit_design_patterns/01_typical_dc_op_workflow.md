---
title: "Typical DC OP workflow"
chapter: "19_circuit_design_patterns"
section: "01_typical_dc_op_workflow"
section_number: "19.1"
topic: "01_typical_dc_op_workflow"
mission_primary: "circuit_design_validation"
mission_secondary: []
related_files:
  - "src/frontend/runcoms.c"
  - "src/spicelib/parser/inp2dot.c"
related_chapters:
  - "../03_analysis_drivers/01_dc_operating_point_dcop.md"
domain_concepts:
  - "dc_workflow"
canonical_chain_tags:
  - "dc_operating_point_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 9
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Typical DC OP workflow {#typical-dc-op-workflow}

## Netlist {#netlist}

Add `.op` (parsed by `dot_op` → `"Operating Point"` job) or simply rely on analyses that require an OP first ([Source: src/spicelib/parser/inp2dot.c#L127-L134]).

## Interactive {#interactive}

Run `op` from nutmeg for the active circuit—`com_op` forwards to `dosim("op", wl)` ([Source: src/frontend/runcoms.c#L122-L126]).

## Validation {#validation}

Cross-check node voltages with `display` / `print v(*)` and ensure `CKTkeepOpInfo` is set when subsequent small-signal analyses need the same bias ([Source: src/include/ngspice/cktdefs.h#L254]).
