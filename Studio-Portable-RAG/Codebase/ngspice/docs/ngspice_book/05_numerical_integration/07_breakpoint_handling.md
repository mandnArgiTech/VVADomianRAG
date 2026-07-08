---
title: "Breakpoint handling"
chapter: "05_numerical_integration"
section: "07_breakpoint_handling"
section_number: "5.7"
topic: "07_breakpoint_handling"
mission_primary: "kernel_reimplementation"
mission_secondary: ["circuit_design_validation"]
related_files:
  - "src/spicelib/analysis/dctran.c"
related_chapters:
  - "../16_command_interpreter/06_breakpoints_and_alter.md"
domain_concepts:
  - "transient_analysis"
canonical_chain_tags:
  - "transient_step_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 8
last_updated_from_source_at: "2026-04-09T03:39:07.072860+00:00"
---

# Breakpoint handling {#breakpoint-handling}

## Overview {#overview}

`DCtran` maintains an ordered breakpoint list `ckt->CKTbreaks` with size `CKTbreakSize`. Initialization seeds at least `[0, finalTime]` ([Source: src/spicelib/analysis/dctran.c#L134-L139]).

During integration, when simulated time passes the next breakpoint, `CKTclrBreak` removes it ([Source: src/spicelib/analysis/dctran.c#L401]). The driver compares `CKTtime` against the next breakpoint using `AlmostEqualUlps` and may shrink `CKTdelta` to land exactly on the breakpoint ([Source: src/spicelib/analysis/dctran.c#L541-L554]).

XSPICE adds additional breakpoint interactions (`g_mif_info.breakpoint`) in the same file ([Source: src/spicelib/analysis/dctran.c#L812-L826]).

<!-- source: src/spicelib/analysis/dctran.c -->

## Source Files {#source-files}

- **`src/spicelib/analysis/dctran.c`**

## Related Chapters {#related-chapters}

- [Breakpoints command](../16_command_interpreter/06_breakpoints_and_alter.md)

## Canonical Chains {#canonical-chains}

- `transient_step_chain`
