---
title: ".noise and .disto"
chapter: "14_netlist_grammar"
section: "07_dot_noise_dot_disto"
section_number: "14.7"
topic: "07_dot_noise_dot_disto"
mission_primary: "circuit_design_validation"
mission_secondary: []
related_files:
  - "src/spicelib/parser/inp2dot.c"
related_chapters:
  - "../03_analysis_drivers/05_noise_analysis_noisean.md"
  - "../03_analysis_drivers/06_distortion_volterra_disto.md"
domain_concepts:
  - "noise_analysis"
  - "distortion_analysis"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 10
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# .noise and .disto {#dot-noise-dot-disto}

## `.noise` grammar {#noise}

`dot_noise` expects `V(...)` output notation, input source name, AC-like sweep keywords, frequency bounds, and optional `ptspersum` ([Source: src/spicelib/parser/inp2dot.c#L35-L84]). The parser binds output/reference nodes into `CKTnode` pointers before attaching analysis parameters.

## `.disto` grammar {#disto}

`dot_disto` mirrors AC sweeps: `DEC|OCT|LIN`, point count, `fstart`, `fstop`, optional `f2overf1` ([Source: src/spicelib/parser/inp2dot.c#L150-L169]).

## Dispatch {#dispatch}

Both are reached from `INP2dot` ([Source: src/spicelib/parser/inp2dot.c#L664-L669]).
