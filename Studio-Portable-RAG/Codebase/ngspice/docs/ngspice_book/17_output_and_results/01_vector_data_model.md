---
title: "Vector data model"
chapter: "17_output_and_results"
section: "01_vector_data_model"
section_number: "17.1"
topic: "01_vector_data_model"
mission_primary: "circuit_design_validation"
mission_secondary: ["kernel_reimplementation"]
related_files:
  - "src/include/ngspice/dvec.h"
  - "src/include/ngspice/plot.h"
related_chapters:
  - "../16_command_interpreter/03_vector_manipulation_commands.md"
domain_concepts:
  - "dvec"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 10
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Vector data model {#vector-data-model}

## `struct dvec` {#struct-dvec}

Each result trace is a `dvec` with name, type, real/complex storage, dimensional metadata (`v_numdims`, `v_dims`), and links into the enclosing plot ([Source: src/include/ngspice/dvec.h#L27-L59]).

## Flags {#flags}

`VF_REAL`, `VF_COMPLEX`, `VF_ACCUM`, `VF_PLOT`, `VF_PRINT`, and `VF_PERMANENT` control how writers and the UI treat the vector ([Source: src/include/ngspice/dvec.h#L8-L18]).

## `struct plot` {#struct-plot}

`plot` aggregates the title, run name (`pl_typename`), head of `pl_dvecs`, independent scale vector, and a hash for `vec_get` speed ([Source: src/include/ngspice/plot.h#L11-L28]).
