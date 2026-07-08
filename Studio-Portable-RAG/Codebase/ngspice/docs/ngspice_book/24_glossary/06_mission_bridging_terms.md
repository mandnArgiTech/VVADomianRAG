---
title: "Mission bridging terms"
chapter: "24_glossary"
section: "06_mission_bridging_terms"
section_number: "24.6"
topic: "06_mission_bridging_terms"
mission_primary: "circuit_design_validation"
mission_secondary: ["kernel_reimplementation"]
related_files:
  - "../../rag_index.json"
related_chapters:
  - "../00_foundations/06_dual_mission_reading_guide.md"
  - "../23_canonical_chains_reference/README.md"
domain_concepts:
  - "dual_mission"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced:
  - "canonical_chain"
  - "kernel_reimplementation"
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 10
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Mission bridging terms {#mission-bridging-terms}

## Dual mission {#dual-mission}

`rag_index.json` describes **kernel reimplementation** (precise call chains) vs **circuit design validation** (netlists, options, outputs)—use it for tags and paths, not as a substitute for reading C ([Source: rag_index.json missions object]).

## Canonical chain {#canonical-chain}

Named end-to-end flows such as `dc_operating_point_chain` with `canonical_members` file lists ([Source: rag_index.json#canonical_chains]).

## NodalAI port {#nodalai-port}

Alternative kernel targeting semantic parity with ngspice’s MNA/NR/device dispatch ([Source: ../22_nodalai_kernel_reimplementation/README.md]).

## Agentic validation {#agentic-validation}

Combines automated regression (`tests/bin/check.sh`) with interactive `.measure`/`.raw` checks ([Source: ../21_validation_with_regression_suite/README.md]).

## Shared library embedding {#shared-library}

`ngSpice_Init` / `ngSpice_Command` APIs for host-driven simulations ([Source: ../01_architecture_overview/05_shared_library_mode.md]).
