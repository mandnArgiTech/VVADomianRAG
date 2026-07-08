---
title: "ngspice: Architecture, Numerical Kernel, and Circuit Design Reference"
type: book_index
generated_at: "2026-05-05T03:08:14.603762Z"
total_chapters: 25
total_sections: 192
book_policy: "LLM_and_human_authored_only_no_book_generator_scripts"
---

# ngspice internal reference book

This document is the **master index** for `docs/ngspice_book/`, a source-grounded companion to the ngspice tree under `Studio-Portable-RAG/Codebase/ngspice/`. The book is written for two overlapping audiences: engineers who need **reliable circuit-simulation practice** on ngspice, and teams building a **NodalAI-style reimplementation** that must match ngspice’s numerical behavior closely enough to serve as an oracle. Every chapter is intended to be read alongside the C and header files it cites; prose claims are anchored with `[Source: path#Lx]` or HTML comments as required by [doument_prompt.md](../../doument_prompt.md). **No Python or other scripts bulk-generate** these Markdown bodies or the `_meta/*.json` artifacts—those files are curated by hand during authoring and review.

The ngspice code base combines a Spice3-derived **frontend** (netlist ingest, nutmeg scripting, measurement, plotting) with a **simulator core** (Modified Nodal Analysis, nonlinear Newton solves, sparse direct linear algebra, and a large catalog of compact device models). The book mirrors that split: early chapters establish shared vocabulary—MNA, Newton–Raphson, Jacobian stamping, convergence tests, integration methods, and sparse LU—while later chapters document how decks become `JOB` records, how results become `dvec`/`plot` structures, and how users should debug failures without guessing.

## How to read this book

If you are **validating analog designs**, start with the foundations and architecture overview, skim the device chapters relevant to your PDK, then live in chapters 14–20 for grammar, options, idioms, and debugging. Treat chapter 21 as your contract-test guide: the upstream `tests/` tree plus `tests/bin/check.sh` is the closest thing ngspice ships to a frozen behavioral specification for many scenarios. If you are **porting the kernel**, read chapters 0–7 and 23 first, then chapter 22 for incremental porting strategy, and only then branch into analysis drivers (chapter 3) and devices (chapters 8–12). Canonical chains in chapter 23 give you end-to-end file lists that should match the mental model you implement in another language; they intentionally overlap with `rag_index.json` but are not a substitute for opening the `.c` files themselves.

Cross-links between chapters use relative Markdown paths. The glossary (chapter 24) collects anchor-friendly definitions for recurring terms—tolerances, ITL limits, `SPICEdev`, `dvec`, and dual-mission vocabulary—so longer chapters can stay focused on control flow.

## Honest omissions

**BSIM6** is not present in this repository’s `src/spicelib/devices/` tree; chapter 11 documents that omission in its README and does not ship a `05_bsim6.md` section. **Chapter 13 (XSPICE)** is included because the configured tree contains XSPICE sources; if your downstream fork disables XSPICE, treat those sections as optional and rely on the preprocessor guards you actually compile.

## Chapter guide

**Chapter 00 – Foundations** introduces SPICE history at a high level, MNA, Newton iteration for nonlinear networks, sparse matrices, transient integration concepts, and the dual-mission reading guide. It orients readers who arrive without Berkeley Spice3 background.

**Chapter 01 – Architecture** walks the layering from `CKTcircuit` through `SPICEdev` registration, shared-library embedding (`sharedspice.c`), and directory layout. It answers “where does this live?” before “how does it work?”.

**Chapter 02 – Numerical kernel core** is the densest mission-1 material: `CKTload`, `NIiter`, convergence testing, damping, junction and FET limiting, and singularity handling. These sections should be line-aligned with `niiter.c`, `niconv.c`, and `cktload.c`.

**Chapter 03 – Analysis drivers** documents `DCop`, sweeps, transient (`DCtran`), AC, noise, distortion, transfer function, sensitivity, pole–zero, and Fourier post-processing at the driver level, always pointing back to the shared NR core.

**Chapters 04–06** cover convergence aids (GMIN/source stepping, pseudo-transient discussion where honest), numerical integration (trap vs Gear, LTE, timestep law), and the sparse solver (including KLU notes where relevant).

**Chapter 07 – Device model contract** explains the `devdefs.h` vtable: `DEVload`, `DEVacLoad`, `DEVtrunc`, `DEVlimit`, temperature hooks, noise, sensitivity, and guidance for adding a device.

**Chapters 08–12** survey passives, sources, diodes/BJTs, MOS families (BSIM3/4, HiSIM, ADMS/EKV notes), and JFET/MESFET/HFET models with emphasis on load routines actually present in-tree.

**Chapter 13 – XSPICE** summarizes event-driven extensions where headers and analysis hooks justify the claims.

**Chapters 14–17** form the mission-2 “front half”: netlist grammar tied to `INP2dot`, parser tokenization (`inp_readall`), subcircuits and numparam, nutmeg commands (`runcoms.c`, `com_*`), and the `dvec`/`plot`/raw/measure/FFT output model.

**Chapter 18** systematizes `.options` parsing via `INPdoOpts` and the `CKTcircuit` tolerance fields. **Chapter 19** collects design workflows (DC, transient, AC, sweeps, corners, optimization outers). **Chapter 20** lists debugging playbooks mapped to real messages and code paths (`CKTop`, `spFactor`, `DCtran`).

**Chapter 21** explains regression layout and `check.sh`. **Chapter 22** gives NodalAI porting strategy. **Chapter 23** enumerates thirteen canonical chains aligned with `rag_index.json`. **Chapter 24** is the glossary.

## Canonical chains and RAG

The repository’s `rag_index.json` (ngspice root) lists `canonical_chains` with `canonical_members` paths and `stages_traversed` labels. Chapter 23 expands each chain into a short narrative that links to deeper sections—for example, `device_load_dispatch_chain` ties `cktload.c` to BSIM4’s `b4ld.c` as a concrete `DEVload`. When automating retrieval, use the JSON for **routing and tagging**, but validate algorithms by reading the cited C.

## Maintenance and validation

Authoring changes should update YAML front matter (`related_files`, `canonical_chain_tags` ⊆ `rag_index.json`), preserve heading anchors `{#...}`, and extend `_meta/cross_reference_index.json` when new cross-chapter links appear. Run through `_meta/manual_validation_checklist.md` before declaring a release-ready snapshot. The curated `_meta/source_file_attribution.json` maps hot-source files to sections for audit—not an exhaustive scrape, but a stable index of where readers should look first.

## Specification link

All structural rules, required headings, and omission policy originate in [doument_prompt.md](../../doument_prompt.md). When in doubt, that document wins.

## Deeper chapter notes

The following notes expand the high-level map above with **reading order hints** and **dependency** information. They are still index-level guidance; the section files contain the citations.

**Foundations and architecture (ch. 0–1).** Read these once, then keep them as reference when terminology drifts. The foundations chapter defines MNA and Newton iteration without binding you to a particular ngspice function name; the architecture chapter immediately grounds those ideas in `CKTcircuit`, `DEVices[]`, and the shared-library entry points. If you are onboarding as a circuit designer, you may skip shared-library detail until you automate ngspice from Python or C++.

**Kernel core (ch. 2).** This chapter is the critical path for NodalAI. Read `CKTload` before any device chapter: every model ultimately serves the dispatcher loop. Then read `NIiter` and convergence testing as a unit, because changing tolerances without understanding `NIconvTest` leads to false “kernel bugs.” Limiting sections (`DEVpnjlim`, `DEVfetlim`) matter disproportionately for robustness; do not treat them as optional polish.

**Analyses (ch. 3).** Each analysis driver reuses the same linearization and solve machinery; differences are mostly in how `CKTmode` is set, which outputs are allocated, and how sweeps advance. When documenting or reimplementing a driver, start from its `JOB` setup in `INP2dot` (chapter 14/15 cross-links) and follow into the corresponding `*an.c` file referenced in chapter 3 sections.

**Convergence, integration, sparse (ch. 4–6).** Chapter 4 connects user-visible aids to `CKTop`’s actual ladder. Chapter 5 is mandatory for transient parity: companion models and LTE drive `DCtran` acceptance. Chapter 6 matters both for performance and for failure diagnosis—singular pivots surface here before they look like device bugs.

**Device contract and catalog (ch. 7–12).** Chapter 7 is the “interface spec” for all devices. Subsequent chapters are organized by device family; within MOS chapters, BSIM4 sections are the default deep reference for industry workflows. Remember the BSIM6 omission: do not assume a section exists just because other simulators ship that model.

**XSPICE (ch. 13).** Treat this as an extension layer: the analog kernel still runs, but event-driven partitions add scheduling concerns. If your build disables XSPICE, skip mechanically but note that some netlists may still contain analog-only content compatible with your build.

**Frontend and outputs (ch. 14–17).** Chapter 14 is the grammar as seen by users; chapter 15 is the same pipeline as seen by `inp_readall` and `INP2dot`. Chapter 16 lists nutmeg commands implemented in `com_*.c` and `runcoms.c`. Chapter 17 explains how results become vectors and files—critical for CI and for machine-learning pipelines that consume `.raw`.

**Options, patterns, debugging (ch. 18–20).** Chapter 18 maps `.options` tokens to `CKTcircuit` fields. Chapter 19 is intentionally methodological: ngspice rarely enforces a single “best” outer loop, so optimization and Monte Carlo are shown as host responsibilities. Chapter 20 ties symptoms to code paths (`spFactor` singularity vs `CKTop` non-convergence vs `DCtran` time quantization).

**Validation, porting, chains (ch. 21–23).** Chapter 21 is about **proof**, not theory: the `tests/` tree is your ground truth for many behaviors. Chapter 22 translates kernel knowledge into a porting plan. Chapter 23 is the shortest way to explain ngspice end-to-end to another engineer: pick a chain, open every file in `canonical_members`, read in order.

**Glossary (ch. 24).** Use it to stabilize vocabulary across chapters and to link dual-mission language to `rag_index.json` without duplicating JSON in prose.

## Suggested curricula

**Three-day kernel skim.** Day 1: ch. 0–2 + ch. 6 sparse overview. Day 2: ch. 3 (DC + TRAN only) + ch. 7 + one MOS load file. Day 3: ch. 23 chains 1–2 + ch. 21 regression mechanics.

**One-week design-focused path.** Ch. 0 (skim), ch. 14–15, ch. 16–17, ch. 18–19, ch. 20, plus device chapters for the models you actually instantiate. Revisit ch. 2 only when debugging NR.

**Embedding / automation path.** Ch. 1 shared library section, ch. 17 raw format, ch. 16 command subset, ch. 23 `shared_lib_api_chain`, then `sharedspice.c` in the source tree.

## Chapter list (quick links)

- [00 foundations](00_foundations/README.md)
- [01 architecture](01_architecture_overview/README.md)
- [02 numerical kernel](02_numerical_kernel_core/README.md)
- [03 analyses](03_analysis_drivers/README.md)
- [04 convergence aids](04_convergence_aids/README.md)
- [05 integration](05_numerical_integration/README.md)
- [06 sparse solver](06_sparse_solver/README.md)
- [07 device contract](07_device_model_contract/README.md)
- [08 passives](08_passive_devices/README.md)
- [09 sources](09_source_devices/README.md)
- [10 diode / BJT](10_diode_and_bjt_models/README.md)
- [11 MOSFET](11_mosfet_models/README.md)
- [12 JFET / MESFET](12_jfet_mesfet_models/README.md)
- [13 XSPICE](13_xspice_mixed_signal/README.md)
- [14 netlist grammar](14_netlist_grammar/README.md)
- [15 parser / expansion](15_parser_and_expansion/README.md)
- [16 command interpreter](16_command_interpreter/README.md)
- [17 output](17_output_and_results/README.md)
- [18 options](18_options_and_tolerances/README.md)
- [19 patterns](19_circuit_design_patterns/README.md)
- [20 debugging](20_debugging_workflows/README.md)
- [21 regression](21_validation_with_regression_suite/README.md)
- [22 NodalAI](22_nodalai_kernel_reimplementation/README.md)
- [23 chains](23_canonical_chains_reference/README.md)
- [24 glossary](24_glossary/README.md)
