---
title: ".tf .sens .pz"
chapter: "14_netlist_grammar"
section: "08_dot_tf_dot_sens_dot_pz"
section_number: "14.8"
topic: "08_dot_tf_dot_sens_dot_pz"
mission_primary: "circuit_design_validation"
mission_secondary: ["kernel_reimplementation"]
related_files:
  - "src/spicelib/parser/inp2dot.c"
related_chapters:
  - "../03_analysis_drivers/07_transfer_function_tfan.md"
  - "../03_analysis_drivers/08_sensitivity_adjoint_senan.md"
  - "../03_analysis_drivers/09_pole_zero_pzan.md"
domain_concepts:
  - "dot_analysis_cards"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 10
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# .tf .sens .pz {#dot-tf-dot-sens-dot-pz}

## Transfer function `.tf` {#tf}

`INP2dot` routes `.tf` to `dot_tf`, which allocates a `"Transfer Function"` job via `ft_find_analysis("TF")` and parses the output reference (`V`/`I` with nodes) plus the small-signal input source ([Source: src/spicelib/parser/inp2dot.c#L290-L318], [Source: src/spicelib/parser/inp2dot.c#L687-L689]).

## Sensitivity `.sens` {#sens}

`.sens` maps to `dot_sens`, building a `"Sensitivity Analysis"` task and parsing the declared output (`v`/`i` with net tokens) before optional `ac`/`dc` modifiers ([Source: src/spicelib/parser/inp2dot.c#L400-L428], [Source: src/spicelib/parser/inp2dot.c#L710-L712]).

## Pole–zero `.pz` {#pz}

`.pz` uses `dot_pz` to register the `PZ` analysis and populate node/output arguments analogously to other small-signal setups ([Source: src/spicelib/parser/inp2dot.c#L207-L239], [Source: src/spicelib/parser/inp2dot.c#L681-L683]).

## Post-run presentation {#presentation}

`.tf` results are also surfaced through `ft_cktcoms`, which detects `plot_list` entries whose typename begins with `tf` and invokes `com_print` ([Source: src/frontend/dotcards.c#L260-L269]).

## See also {#see-also}

Kernel behavior for these analyses lives in [chapter 3](../03_analysis_drivers/README.md).
