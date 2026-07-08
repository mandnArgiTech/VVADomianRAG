---
title: "Dual-mission reading guide"
chapter: "00_foundations"
section: "06_dual_mission_reading_guide"
section_number: "0.6"
topic: "06_dual_mission_reading_guide"
mission_primary: "circuit_design_validation"
mission_secondary: ["kernel_reimplementation"]
related_files: []
related_chapters:
  - "../14_netlist_grammar/README.md"
  - "../02_numerical_kernel_core/README.md"
  - "../24_glossary/README.md"
domain_concepts: []
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "new circuit designer"
  - "NodalAI reimplementer"
estimated_reading_minutes: 8
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Dual-mission reading guide {#dual-mission-reading-guide}

## Overview {#overview}

This book is written for two retrieval missions described in [`doument_prompt.md`](../../../doument_prompt.md) and summarized in `rag_index.json#missions`:

1. **Kernel reimplementation** — Recover algorithms, data invariants, and call chains faithful enough to re-code the ngspice numerical core (Newton loop, device dispatch, sparse solve, transient integration).
2. **Circuit design and validation** — Understand netlists, dot commands, tolerances, outputs, and debugging workflows for autonomous or human-in-the-loop design agents.

Every chapter front matter includes `mission_primary` / `mission_secondary` YAML to steer RAG toward the right audience mix.

## How to Read for Kernel Reimplementation {#kernel-path}

Follow this spine:

1. [Architecture overview](../01_architecture_overview/README.md) — where `CKTcircuit`, `DEVices`, and analysis drivers live.
2. [Numerical kernel core](../02_numerical_kernel_core/README.md) — `CKTload`, `NIiter`, convergence, limiters, singularity handling.
3. [Analysis drivers](../03_analysis_drivers/README.md) — how `DCop`, `DCtran`, etc., call the kernel.
4. [Convergence aids](../04_convergence_aids/README.md) and [integration](../05_numerical_integration/README.md) — outer loops around NR.
5. [Sparse solver](../06_sparse_solver/README.md) — `SMP*` factor/solve semantics.
6. [Device contract](../07_device_model_contract/README.md) then [devices 8–12](../08_passive_devices/README.md) — per-model stamping rules.

Use [Canonical chains](../23_canonical_chains_reference/README.md) when you need end-to-end traces (DCOP, transient step, device dispatch).

## How to Read for Circuit Design & Validation {#design-path}

Prioritize:

1. [Netlist grammar](../14_netlist_grammar/README.md) and [Parser / expansion](../15_parser_and_expansion/README.md).
2. [Command interpreter](../16_command_interpreter/README.md) and [Output / results](../17_output_and_results/README.md) (especially raw format).
3. [Options & tolerances](../18_options_and_tolerances/README.md) — links symptom (non-convergence) to knobs (`RELTOL`, `ITL*`, `GMIN`, …).
4. [Debugging workflows](../20_debugging_workflows/README.md) and [Regression validation](../21_validation_with_regression_suite/README.md).

Mission-1 chapters still help when you need *why* a `.option` matters numerically.

## Cross-Linking Convention {#cross-links}

- Section bodies cite C/H sources with `<!-- source: path -->` or `[Source: path#Lx-Ly]`.
- `related_chapters` in YAML mirrors Markdown “Related Chapters” lists—keep them aligned when you edit.

## Related Chapters {#related-chapters}

- [What is SPICE / ngspice](01_what_is_spice_and_ngspice.md) — object-level introduction.
- [Glossary hub](../24_glossary/README.md) — term → anchor map (authored in Chapter 24).

## Source Files {#source-files}

- Policy and schema: [`doument_prompt.md`](../../../doument_prompt.md), [`rag_index.json`](../../../rag_index.json).
