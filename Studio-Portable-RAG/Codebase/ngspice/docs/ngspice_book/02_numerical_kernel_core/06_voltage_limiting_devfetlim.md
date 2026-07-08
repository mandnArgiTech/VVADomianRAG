---
title: "FET limiting (DEVfetlim)"
chapter: "02_numerical_kernel_core"
section: "06_voltage_limiting_devfetlim"
section_number: "2.6"
topic: "06_voltage_limiting_devfetlim"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/spicelib/devices/devsup.c"
  - "src/include/ngspice/devdefs.h"
related_chapters:
  - "05_voltage_limiting_devpnjlim.md"
  - "../11_mosfet_models/04_bsim4.md"
domain_concepts:
  - "device_model_contract"
canonical_chain_tags:
  - "device_load_dispatch_chain"
numerical_invariants_introduced: []
glossary_terms_introduced:
  - "DEVfetlim"
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 9
last_updated_from_source_at: "2026-04-09T03:39:07.104114+00:00"
---

# FET limiting (DEVfetlim) {#voltage-limiting-devfetlim}

## Overview {#overview}

`DEVfetlim` bounds per-iteration changes on FET terminal voltages (e.g., `vgs`, `vgd`) relative to threshold voltage `vto`, preventing huge swings while the Newton loop approaches the solution ([Source: src/spicelib/devices/devsup.c#L93-L120]).

<!-- source: src/spicelib/devices/devsup.c -->

## What This Module Does {#what-it-does}

Computes test windows `vtsthi`, `vtstlo`, and `vtox = vto + 3.5`, inspects the direction `delv = vnew - vold`, and piecewise clamps `vnew` depending on whether `vold` is above or below threshold ([Source: src/spicelib/devices/devsup.c#L109-L120] — logic continues below line 120 in source).

## Diagnostics {#diagnostics}

When the returned voltage differs from the original trial and diagnostic hooks are enabled, `ngspice_diag_emit_limiter_fet` logs the event ([Source: src/spicelib/devices/devsup.c#L158-L161]).

## Source Files {#source-files}

- **`src/spicelib/devices/devsup.c`**
- **`src/include/ngspice/devdefs.h`**

## Related Chapters {#related-chapters}

- [Junction limiting](05_voltage_limiting_devpnjlim.md)
- [BSIM4 chapter](../11_mosfet_models/04_bsim4.md) — model-specific use inside `*load.c`.

## Glossary {#glossary}

- **DEVfetlim** — FET gate-related voltage limiter; see [Device modeling terms](../24_glossary/02_device_modeling_terms.md#device-modeling-terms).
