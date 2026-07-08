---
title: "Dot command overview"
chapter: "14_netlist_grammar"
section: "03_dotcommand_overview"
section_number: "14.3"
topic: "03_dotcommand_overview"
mission_primary: "circuit_design_validation"
mission_secondary: []
related_files:
  - "src/spicelib/parser/inp2dot.c"
  - "src/frontend/dotcards.c"
related_chapters:
  - "../15_parser_and_expansion/02_dotcommand_dispatch.md"
domain_concepts:
  - "dot_commands"
canonical_chain_tags:
  - "netlist_to_simulation_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 9
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Dot command overview {#dotcommand-overview}

## Parser vs interactive {#parser-vs-interactive}

`INP2dot` is the **batch netlist** switchboard: it recognizes `.op`, `.dc`, `.ac`, `.tran`, `.tf`, `.noise`, `.sens`, `.options`, `.end`, and explicitly ignores `.meas`/`.param` for later frontend handling ([Source: src/spicelib/parser/inp2dot.c#L659-L739]).

## Post-simulation dot execution {#post-sim}

After `dosim` finishes, accumulated commands in `ci_commands` feed helpers like `ft_cktcoms`, which pretty-prints operating-point vectors and runs `.plot`/`.print` compatibility paths ([Source: src/frontend/dotcards.c#L184-L212], [Source: src/frontend/runcoms.c#L359-L361]).

## Obsolete cards {#obsolete}

`.print`/`.plot`/`.width` inside `INP2dot` emit warnings and are ignored in favor of nutmeg commands ([Source: src/spicelib/parser/inp2dot.c#L647-L651]).
