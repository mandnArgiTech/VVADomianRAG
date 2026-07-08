---
title: "Porting BSIM4 pragmatically"
chapter: "22_nodalai_kernel_reimplementation"
section: "07_porting_bsim4_pragmatically"
section_number: "22.7"
topic: "porting_bsim4_pragmatically"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/spicelib/devices/bsim4/b4ld.c"
  - "src/include/ngspice/devdefs.h"
related_chapters:
  - "../11_mosfet_models/04_bsim4.md"
  - "../23_canonical_chains_reference/04_device_load_dispatch_chain.md"
domain_concepts:
  - "bsim4_porting"
canonical_chain_tags:
  - "device_load_dispatch_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 11
last_updated_from_source_at: "2026-05-05T03:08:14.603762Z"
---

# Porting BSIM4 pragmatically {#porting-bsim4-pragmatically}

## Interface before physics {#interface}

`BSIM4load` is the concrete `DEVload` implementation reached through the same `DEVices[]` indirection as every other model ([Source: src/spicelib/devices/bsim4/b4ld.c#L72], [Source: src/spicelib/analysis/cktload.c#L61-L64]). Porting should start by matching:

- Terminal ordering and **internal node** handling (`QB`, `QD`, etc. as used in ngspice’s instance struct).
- Which **charges/capacitances** participate in transient (`Q` derivatives) vs DC-only simplifications.

## Layered verification {#verification}

1. **IV sweeps** (`ids` vs `vgs`) with all capacitors turned off or fixed bias—validates core current model.
2. **CV small-signal** checks against ngspice `.ac` at fixed bias.
3. **GIDL/GISL and stress parameters** last—they interact with limiting and `NIconvTest` in subtle ways.

## When *not* to transliterate {#when-not}

If your goal is inference-friendly code, consider generating simplified surrogate models from ngspice golden data; still keep a **thin BSIM4 compatibility mode** for sign-off.
