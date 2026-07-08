---
title: "Parser error handling"
chapter: "15_parser_and_expansion"
section: "06_parser_error_handling"
section_number: "15.6"
topic: "06_parser_error_handling"
mission_primary: "circuit_design_validation"
mission_secondary: []
related_files:
  - "src/spicelib/parser/inpdoopt.c"
  - "src/include/ngspice/iferrmsg.h"
related_chapters:
  - "../20_debugging_workflows/README.md"
domain_concepts:
  - "parser_errors"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 9
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Parser error handling {#parser-error-handling}

## Option-card errors {#option-card}

`INPdoOpts` concatenates warnings via `INPerrCat` when `setAnalysisParm` fails or when an option keyword is unknown ([Source: src/spicelib/parser/inpdoopt.c#L61-L75]).

## Simulator error taxonomy {#simulator-taxonomy}

Once parsing finishes, runtime failures use `E_*` codes and optional `errMsg` strings described in `iferrmsg.h` ([Source: src/include/ngspice/iferrmsg.h#L15-L56]).

## User workflow {#workflow}

Treat stderr lines from `INPdoOpts` as **hard configuration problems** (typos in `.options`), distinct from NR convergence errors that surface later in `CKTop`/`NIiter`.
