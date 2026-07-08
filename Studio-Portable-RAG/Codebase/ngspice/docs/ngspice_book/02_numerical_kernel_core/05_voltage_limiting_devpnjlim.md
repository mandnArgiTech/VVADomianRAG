---
title: "Junction limiting (DEVpnjlim)"
chapter: "02_numerical_kernel_core"
section: "05_voltage_limiting_devpnjlim"
section_number: "2.5"
topic: "05_voltage_limiting_devpnjlim"
mission_primary: "kernel_reimplementation"
mission_secondary: ["circuit_design_validation"]
related_files:
  - "src/spicelib/devices/devsup.c"
  - "src/include/ngspice/devdefs.h"
related_chapters:
  - "../07_device_model_contract/07_devlimit_per_device_limiting.md"
  - "06_voltage_limiting_devfetlim.md"
domain_concepts:
  - "device_model_contract"
canonical_chain_tags:
  - "device_load_dispatch_chain"
numerical_invariants_introduced: []
glossary_terms_introduced:
  - "DEVpnjlim"
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 10
last_updated_from_source_at: "2026-04-09T03:39:07.104114+00:00"
---

# Junction limiting (DEVpnjlim) {#voltage-limiting-devpnjlim}

## Overview {#overview}

`DEVpnjlim` clamps large per-iteration changes of PN junction voltages—used throughout diode and bipolar MOS body junction paths—to prevent exponential overflow and Newton oscillation. The routine lives in `devsup.c` alongside other shared limiters ([Source: src/spicelib/devices/devsup.c#L45-L90]).

Prototype:

```16:18:Studio-Portable-RAG/Codebase/ngspice/src/include/ngspice/devdefs.h
double DEVlimvds(double,double);
double DEVpnjlim(double,double,double,double,int*);
double DEVfetlim(double,double,double);
```

<!-- source: src/spicelib/devices/devsup.c -->
<!-- source: src/include/ngspice/devdefs.h -->

## What This Module Does {#what-it-does}

Given a trial junction voltage `vnew`, previous iterate `vold`, thermal voltage `vt`, critical voltage `vcrit`, and `icheck` flag, it returns a limited voltage and signals whether limiting occurred ([Source: src/spicelib/devices/devsup.c#L52-L90]).

## Algorithm In Detail {#algorithm}

1. **High forward bias** — If `vnew > vcrit` *and* `|vnew - vold| > 2*vt`, apply a logarithmic correction that depends on the direction of change ([Source: src/spicelib/devices/devsup.c#L57-L67]).
2. **Negative region** — Additional clamps when `vnew < 0`, comparing against functions of `vold` ([Source: src/spicelib/devices/devsup.c#L70-L84]).
3. **Diagnostics** — When limiting fires and diagnostic hooks enabled, emit structured JSON via `ngspice_diag_emit_limiter_pnj` ([Source: src/spicelib/devices/devsup.c#L86-L89]).

## Usage Pattern {#usage}

Device `DEVload` functions call `DEVpnjlim` on internal junction variables before evaluating exponentials—see diode load (`dioload.c`) and VBIC (`vbicload.c`) in the source tree.

## Source Files {#source-files}

- **`src/spicelib/devices/devsup.c`** — implementation.
- **`src/include/ngspice/devdefs.h`** — prototype.

## Related Chapters {#related-chapters}

- [DEVlimit note](../07_device_model_contract/07_devlimit_per_device_limiting.md) — ngspice centralizes some limiting as helpers rather than a single `DEVlimit` pointer.
- [FET limiting](06_voltage_limiting_devfetlim.md)

## Canonical Chains {#canonical-chains}

- `device_load_dispatch_chain` — invoked from many `DEVload` paths.

## Glossary {#glossary}

- **DEVpnjlim** — PN junction voltage limiter; see [Device modeling terms](../24_glossary/02_device_modeling_terms.md#device-modeling-terms).
