---
title: "DEVconvTest"
chapter: "07_device_model_contract"
section: "06_devconvtest_per_device_convergence"
section_number: "7.6"
topic: "06_devconvtest_per_device_convergence"
mission_primary: "kernel_reimplementation"
mission_secondary: []
related_files:
  - "src/include/ngspice/devdefs.h"
  - "src/spicelib/analysis/cktop.c"
  - "src/spicelib/devices/bsim4/bsim4init.c"
related_chapters:
  - "../02_numerical_kernel_core/03_convergence_test_anatomy.md"
domain_concepts:
  - "convergence_test"
canonical_chain_tags:
  - "dc_operating_point_chain"
numerical_invariants_introduced:
  - "convergence_test"
glossary_terms_introduced: []
audience:
  - "NodalAI reimplementer"
estimated_reading_minutes: 7
last_updated_from_source_at: "2026-04-09T03:39:07.065678+00:00"
---

# DEVconvTest (per-device convergence) {#devconvtest-per-device-convergence}

## Overview {#overview}

`DEVconvTest` allows devices to enforce additional convergence criteria beyond the algebraic `NIconvTest`. The vtable slot is `int (*DEVconvTest)(GENmodel*, CKTcircuit*)` ([Source: src/include/ngspice/devdefs.h#L86-L87]). BSIM4 supplies `BSIM4convTest` ([Source: src/spicelib/devices/bsim4/bsim4init.c#L61]).

`CKTconvTest` walks all device types analogously to `CKTload` ([Source: src/spicelib/analysis/cktop.c#L98-L111]).

When `NEWCONV` is enabled, `NIconvTest` chains into `CKTconvTest` after the row-wise check ([Source: src/maths/ni/niconv.c#L68-L74]).

<!-- source: src/include/ngspice/devdefs.h -->
<!-- source: src/spicelib/analysis/cktop.c -->
<!-- source: src/maths/ni/niconv.c -->

## Source Files {#source-files}

- **`src/include/ngspice/devdefs.h`**
- **`src/spicelib/analysis/cktop.c`**
- **`src/maths/ni/niconv.c`**

## Related Chapters {#related-chapters}

- [Convergence test anatomy](../02_numerical_kernel_core/03_convergence_test_anatomy.md)
