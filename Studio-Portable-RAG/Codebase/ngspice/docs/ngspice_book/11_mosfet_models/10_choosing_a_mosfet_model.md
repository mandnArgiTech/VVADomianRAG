---
title: "Choosing a MOSFET model"
chapter: "11_mosfet_models"
section: "10_choosing_a_mosfet_model"
section_number: "11.9"
topic: "10_choosing_a_mosfet_model"
mission_primary: "circuit_design_validation"
mission_secondary: ["kernel_reimplementation"]
related_files:
  - "src/spicelib/devices/dev.c"
related_chapters:
  - "04_bsim4.md"
  - "../18_options_and_tolerances/README.md"
domain_concepts:
  - "device_model_contract"
canonical_chain_tags: []
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "advanced circuit designer"
estimated_reading_minutes: 9
last_updated_from_source_at: "2026-04-09T03:39:07.104114+00:00"
---

# Choosing a MOSFET model {#choosing-a-mosfet-model}

## Overview {#overview}

From a **netlist** perspective, model choice is driven by the `.model` card and the corresponding entry in ngspice’s device table (`static_devices[]` lists the compiled-in models such as `mos1`, `bsim4`, `hisim2`, [Source: src/spicelib/devices/dev.c#L287-L295]).

## Practical guidance {#guidance}

| Need | Suggested starting point |
|------|---------------------------|
| Legacy compatibility / teaching | Levels 1–3 ([`mos1load.c`](../01_mosfet_levels_1_2_3.md)) |
| Foundry PDK alignment | BSIM4 ([`b4ld.c`](04_bsim4.md)) |
| Surface-potential accuracy | HiSIM2 ([`hsm2ld.c`](07_hisim2.md)) |
| HV IC | HiSIM-HV tree ([`hisimhv1/`](08_hisim_hv2.md)) |

## Omissions {#omissions}

BSIM6 is **not** present in this repository—there is no `devices/bsim6/` tree, so no `05_bsim6.md` section file is shipped.

## Source Files {#source-files}

- **`src/spicelib/devices/dev.c`** — enumerates linked model families.

## Related Chapters {#related-chapters}

- [BSIM4](04_bsim4.md)
- [Options & tolerances](../18_options_and_tolerances/README.md)
