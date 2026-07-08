---
title: "Print and save options"
chapter: "18_options_and_tolerances"
section: "07_print_save_options"
section_number: "18.7"
topic: "07_print_save_options"
mission_primary: "circuit_design_validation"
mission_secondary: []
related_files:
  - "src/frontend/rawfile.c"
  - "src/frontend/dotcards.c"
related_chapters:
  - "../17_output_and_results/README.md"
domain_concepts:
  - "output_options"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 8
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Print and save options {#print-save-options}

## Precision {#precision}

`raw_prec` (defaulting to 15 significant figures) overrides how `raw_write` formats ASCII columns ([Source: src/frontend/rawfile.c#L24-L26], [Source: src/frontend/rawfile.c#L59-L60]).

## Padding {#padding}

`nopadding` as a bool variable removes alignment padding when serializing rawfiles ([Source: src/frontend/rawfile.c#L51]).

## `.save` integration {#save-integration}

`ft_dotsaves` still funnels `.save` directives into `com_save`, ensuring vectors survive garbage collection ([Source: src/frontend/dotcards.c#L56-L75]).
