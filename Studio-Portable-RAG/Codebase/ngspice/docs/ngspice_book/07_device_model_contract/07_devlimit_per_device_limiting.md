---
title: "DEVlimit and shared limiters"
chapter: "07_device_model_contract"
section: "07_devlimit_per_device_limiting"
section_number: "7.7"
topic: "07_devlimit_per_device_limiting"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/include/ngspice/devdefs.h"
  - "src/spicelib/devices/devsup.c"
related_chapters:
  - "../02_numerical_kernel_core/05_voltage_limiting_devpnjlim.md"
  - "../02_numerical_kernel_core/06_voltage_limiting_devfetlim.md"
domain_concepts:
  - "device_model_contract"
canonical_chain_tags:
  - "device_load_dispatch_chain"
numerical_invariants_introduced: []
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 6
last_updated_from_source_at: "2026-04-09T03:39:07.104114+00:00"
---

# DEVlimit and shared limiters {#devlimit-per-device-limiting}

## Overview {#overview}

Unlike some SPICE documentation templates, the `SPICEdev` structure in ngspice **does not** expose a `DEVlimit` function pointer. Instead, limiting is performed inside `DEVload` implementations using shared helpers declared next to the struct: `DEVpnjlim`, `DEVfetlim`, `DEVlimvds`, etc. ([Source: src/include/ngspice/devdefs.h#L16-L23], implementations in [Source: src/spicelib/devices/devsup.c#L23-L163]).

<!-- source: src/include/ngspice/devdefs.h -->
<!-- source: src/spicelib/devices/devsup.c -->

## What This Section Does {#what-it-does}

Prevents reimplementers from searching for a nonexistent vtable slot: limiters are *library routines* called from device code, not a second dispatch path from `NIiter`.

## Source Files {#source-files}

- **`src/include/ngspice/devdefs.h`**
- **`src/spicelib/devices/devsup.c`**

## Related Chapters {#related-chapters}

- [DEVpnjlim](../02_numerical_kernel_core/05_voltage_limiting_devpnjlim.md)
- [DEVfetlim](../02_numerical_kernel_core/06_voltage_limiting_devfetlim.md)
