---
title: "Known porting pitfalls"
chapter: "22_nodalai_kernel_reimplementation"
section: "08_known_porting_pitfalls"
section_number: "22.8"
topic: "known_porting_pitfalls"
mission_primary: "kernel_reimplementation"
mission_secondary: ["circuit_design_validation"]
related_files:
  - "src/spicelib/analysis/ckttrunc.c"
  - "src/maths/ni/niinteg.c"
related_chapters:
  - "../20_debugging_workflows/README.md"
  - "../04_convergence_aids/README.md"
domain_concepts:
  - "porting_pitfalls"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 10
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Known porting pitfalls {#known-porting-pitfalls}

## Floating-point and ordering {#floating-point}

Even with identical algorithms, **pivot order** and **FMA usage** can shift last-bit results. Regression compares filtered text with `diff -B -w` ([Source: tests/bin/check.sh#L44-L46]); adopt similar looseness or compare metrics (RMS voltage error) on vectors.

## Timestep coupling {#timestep}

`CKTtrunc` merges device-proposed deltas; getting LTE wrong manifests as “works at big steps, explodes at small ones” ([Source: ../05_numerical_integration/06_timestep_control_law.md]). Always validate transient after DCOP matches.

## Convergence aids hidden state {#convergence-aids}

GMIN/source stepping modifies the effective circuit. If your port skips `CKTop`’s ladder, difficult netlists will diverge from ngspice despite a correct NR core ([Source: ../04_convergence_aids/01_convergence_aid_ladder.md]).

## Subcircuit / parameter expansion {#subckt}

Elaboration order changes device instance counts. Diff the **flattened** netlist (node names included) before chasing Jacobian bugs ([Source: ../15_parser_and_expansion/03_subcircuit_expansion_mechanics.md]).
