---
title: "Save and load state"
chapter: "16_command_interpreter"
section: "07_save_load_state"
section_number: "16.7"
topic: "07_save_load_state"
mission_primary: "circuit_design_validation"
mission_secondary: []
related_files:
  - "src/frontend/dotcards.c"
  - "src/frontend/rawfile.c"
related_chapters:
  - "../17_output_and_results/02_raw_file_format_spec.md"
domain_concepts:
  - "save_restore"
canonical_chain_tags:
  - "raw_output_consumption_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 8
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Save and load state {#save-load-state}

## `.save` → `com_save` {#save}

`ft_dotsaves` gathers `.save` directives from `ci_commands` and funnels them into `com_save`, which registers vectors for automatic retention ([Source: src/frontend/dotcards.c#L56-L75]).

## Raw snapshots {#raw}

`raw_write` persists an entire `struct plot` to disk in ASCII or binary form ([Source: src/frontend/rawfile.c#L34-L57]).

## Reload {#reload}

`raw_read` (declared in `fteext.h`) rebuilds plots for later `setplot` inspection—useful when comparing two ngspice versions offline.
