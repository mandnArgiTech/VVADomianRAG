---
title: "Python equivalents for the C kernel"
chapter: "22_nodalai_kernel_reimplementation"
section: "03_python_equivalents_for_c_kernel"
section_number: "22.3"
topic: "python_equivalents_for_c_kernel"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/include/ngspice/devdefs.h"
  - "src/maths/ni/niiter.c"
related_chapters:
  - "../02_numerical_kernel_core/02_newton_raphson_iteration_niiter.md"
domain_concepts:
  - "python_prototyping"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 10
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Python equivalents for the C kernel {#python-equivalents-for-c-kernel}

## Structural mapping {#structural-mapping}

| C concept | Practical Python stand-in |
|-----------|---------------------------|
| `SPICEdev` vtable | `dataclass` + `Dict[str, Callable]` or a small protocol class per device |
| `DEVices[i]->DEVload` | Registry `loads[device_key](instance, ckt_view)` mirroring [devdefs.h](src/include/ngspice/devdefs.h#L47-L117) |
| `NIiter` loop | `for it in range(max_iter): build_J_and_rhs(); solve(); if converged: break` ([Source: src/maths/ni/niiter.c#L29]) |
| Sparse LU | `scipy.sparse.linalg.splu` or custom `scikit-sparse` if pattern is fixed |

## Preserve semantics, not syntax {#semantics}

Python prototypes should log **stamp coordinates** (row, col, value) and **RHS entries** per iteration to diff against ngspice’s debug prints or a small C hook. The goal is to catch sign errors in controlled sources and companion models early.

## Performance path {#performance}

Once numerics match, hot paths can move to **NumPy vectorized** device evaluations or a **Rust/C extension** while keeping the Python `NIiter` orchestration for experimentation.
