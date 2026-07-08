---
title: "Reading reference outputs"
chapter: "21_validation_with_regression_suite"
section: "03_reading_reference_outputs"
section_number: "21.3"
topic: "reading_reference_outputs"
mission_primary: "circuit_design_validation"
mission_secondary: []
related_files:
  - "tests/bin/check.sh"
related_chapters:
  - "../17_output_and_results/02_raw_file_format_spec.md"
domain_concepts:
  - "reference_output"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 8
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Reading reference outputs {#reading-reference-outputs}

## What `*.out` contains {#contents}

Reference files are **text captures** of ngspice’s stdout for the accompanying `.cir`, not necessarily binary `.raw` dumps. They include banners, iteration logs, and printed vectors depending on the netlist.

## Filtering philosophy {#filtering}

`check.sh` strips noisy lines (timestamps, CPU messages, certain analysis banners) before `diff` ([Source: tests/bin/check.sh#L20]). When you eyeball a failure:

1. Compare the **filtered** views first (what CI uses).
2. If still unclear, diff the full `*.test` vs `*.out` to see whether the mismatch is cosmetic.

## Binary raw side path {#raw}

Some workflows save `.raw` separately; parsing rules live in [chapter 17](../17_output_and_results/02_raw_file_format_spec.md). The stock regression harness, however, focuses on stdout text.
