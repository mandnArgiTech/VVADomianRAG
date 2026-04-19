# STORY I: ngspice C Diagnostic Instrumentation — AI-Ready Convergence Trace

**Repository:** `mandnArgiTech/VVADomianRAG` (ngspice source at `Studio-Portable-RAG/Codebase/ngspice/src`)
**Priority:** High
**Estimated effort:** 4–5 hours
**Files to modify:** 5 ngspice C source files + 1 new header
**Files to create:** `src/include/ngspice/diaghooks.h`

---

## Business Context

When NodalAI fails to converge on a benchmark circuit, the AI agent (Cursor/Claude) currently:

1. Runs ngspice on the same circuit → gets final node voltages (pass/fail)
2. Compares voltages → finds which nodes differ
3. Searches the RAG for ngspice source code → reads how the algorithm SHOULD work
4. **Guesses** why NodalAI diverges — because ngspice's internal state during simulation is invisible

Step 4 is a black box. The AI can read the `DEVpnjlim` source code but can't see:
- Did the limiter actually fire on this circuit? At what voltage?
- How many NR iterations did ngspice need? What was the max residual at each step?
- Did GMIN stepping activate? At what level did it converge?
- What were the device conductances (gd, gm) at each iteration?
- Was the Jacobian well-conditioned or nearly singular?

**This story adds ~50 lines of `fprintf` instrumentation across 5 ngspice C files** that dump structured JSON Lines to a diagnostic trace file. The AI agent reads this `.diag.jsonl` file after simulation and gets a complete numerical record of HOW ngspice converged — not just THAT it converged.

**Zero performance overhead when disabled.** All hooks are guarded by a single `DIAG_EMIT()` macro that checks a `FILE*` pointer — when the pointer is NULL (default), the macro is a no-op.

---

## Architecture

### Activation

Set the `NGSPICE_DIAG_FILE` environment variable before running ngspice:

```bash
NGSPICE_DIAG_FILE=circuit.diag.jsonl ngspice -b circuit.cir
```

When unset, no diagnostic file is created and all hooks are zero-cost.

### Output Format

JSON Lines (one JSON object per line), easily parsed by Python `json.loads()`:

```jsonl
{"hook":"nr_iter","iter":1,"max_rhs":2.3e-1,"max_dx":4.5e-1,"damp":1.0,"conv":0}
{"hook":"limiter","fn":"DEVpnjlim","vnew_raw":1.20,"vnew_lim":0.68,"vold":0.55,"vcrit":0.60}
{"hook":"device","type":"DIO","inst":"d1","vd":0.68,"id":2.1e-3,"gd":8.1e-2,"ieq":1.5e-3}
{"hook":"nr_iter","iter":2,"max_rhs":3.1e-3,"max_dx":1.2e-2,"damp":1.0,"conv":0}
{"hook":"nr_iter","iter":12,"max_rhs":8.2e-13,"max_dx":4.1e-8,"damp":1.0,"conv":1}
{"hook":"gmin","val":1.0e-3,"conv":1,"iters":8}
{"hook":"gmin","val":1.0e-4,"conv":1,"iters":5}
{"hook":"matrix","size":15,"min_piv":2.3e-6,"max_piv":1.1e+3,"ratio":4.8e+8}
```

### Macro

```c
/* src/include/ngspice/diaghooks.h */
#ifndef NGSPICE_DIAGHOOKS_H
#define NGSPICE_DIAGHOOKS_H

#include <stdio.h>

extern FILE *ngspice_diag_fp;

#define DIAG_EMIT(...) \
    do { if (ngspice_diag_fp) fprintf(ngspice_diag_fp, __VA_ARGS__); } while (0)

/* Call once at startup (e.g., in main.c or INPpas1) */
void ngspice_diag_init(void);

/* Call once at shutdown */
void ngspice_diag_close(void);

#endif /* NGSPICE_DIAGHOOKS_H */
```

---

## Acceptance Criteria

### AC-1: `diaghooks.h` header and init/close functions

**Given** a new file `src/include/ngspice/diaghooks.h`,
**When** included by any ngspice C file,
**Then** it provides:
- `extern FILE *ngspice_diag_fp` — global pointer, NULL by default
- `DIAG_EMIT(fmt, ...)` — macro that does `fprintf(ngspice_diag_fp, ...)` only when pointer is non-NULL
- `ngspice_diag_init()` — reads `NGSPICE_DIAG_FILE` env var, opens file for writing, sets pointer
- `ngspice_diag_close()` — flushes and closes file, sets pointer to NULL

**Implementation file:** `src/misc/diaghooks.c` (or inline in an existing misc file)

```c
#include "ngspice/diaghooks.h"
#include <stdlib.h>

FILE *ngspice_diag_fp = NULL;

void ngspice_diag_init(void) {
    const char *path = getenv("NGSPICE_DIAG_FILE");
    if (path && path[0]) {
        ngspice_diag_fp = fopen(path, "w");
        if (!ngspice_diag_fp)
            fprintf(stderr, "WARNING: cannot open diag file %s\n", path);
    }
}

void ngspice_diag_close(void) {
    if (ngspice_diag_fp) {
        fflush(ngspice_diag_fp);
        fclose(ngspice_diag_fp);
        ngspice_diag_fp = NULL;
    }
}
```

### AC-2: Hook 1 — NR iteration trace

**File:** `src/maths/ni/niiter.c`, inside `NIiterate()` (or the equivalent DC iteration function)

**After each NR iteration completes** (after convergence check, before the next iteration or return), emit:

```c
#include "ngspice/diaghooks.h"

/* Inside the iteration loop, after convergence test */
DIAG_EMIT("{\"hook\":\"nr_iter\",\"iter\":%d,\"max_rhs\":%.6e,\"max_dx\":%.6e,\"damp\":%.4f,\"conv\":%d}\n",
    ckt->CKTstat->STATnumIter,    /* iteration count */
    ckt->CKTstat->STATmaxRHS,     /* max KCL residual (‖F‖∞) */
    ckt->CKTstat->STATmaxDelta,   /* max voltage change (‖Δx‖∞) */
    ckt->CKTdamping,              /* damping factor (1.0 = undamped) */
    converged                     /* 0 or 1 */
);
```

**Note:** The exact variable names for max residual and max delta may differ from the domain doc pseudocode. Check the actual `niiter.c` source. The key values are:
- `max_rhs`: Maximum absolute value of the RHS vector after device load (KCL violation)
- `max_dx`: Maximum absolute voltage change between iterations
- `damp`: Current damping factor
- `conv`: Whether this iteration passed the convergence test

### AC-3: Hook 2 — Device limiter activation

**File:** `src/spicelib/devices/devsup.c`, inside `DEVpnjlim()`

**When the limiter fires** (the `*icheck = 1` path), emit:

```c
#include "ngspice/diaghooks.h"

/* Inside DEVpnjlim, ONLY when limiting actually occurs (*icheck = 1) */
DIAG_EMIT("{\"hook\":\"limiter\",\"fn\":\"DEVpnjlim\",\"vnew_raw\":%.6e,\"vnew_lim\":%.6e,\"vold\":%.6e,\"vcrit\":%.6e}\n",
    vnew_before_limiting,  /* save vnew at function entry */
    vnew,                  /* vnew after limiting */
    vold,                  /* previous iteration voltage */
    vcrit                  /* critical voltage threshold */
);
```

**Implementation detail:** Save `vnew` at the top of `DEVpnjlim` before any modification:

```c
double DEVpnjlim(double vnew, double vold, double vt, double vcrit, int *icheck)
{
    double vnew_orig = vnew;  /* ADD THIS LINE */
    double arg;

    /* ... existing limiting logic ... */

    /* ADD: emit diagnostic only when limiting occurred */
    if (*icheck) {
        DIAG_EMIT("{\"hook\":\"limiter\",\"fn\":\"DEVpnjlim\",\"vnew_raw\":%.6e,\"vnew_lim\":%.6e,\"vold\":%.6e,\"vcrit\":%.6e}\n",
            vnew_orig, vnew, vold, vcrit);
    }

    return(vnew);
}
```

Similarly for `DEVfetlim()` in the same file:

```c
DIAG_EMIT("{\"hook\":\"limiter\",\"fn\":\"DEVfetlim\",\"vnew_raw\":%.6e,\"vnew_lim\":%.6e,\"vold\":%.6e,\"vto\":%.6e}\n",
    vnew_orig, vnew, vold, vto);
```

### AC-4: Hook 3 — GMIN / source stepping

**File:** `src/spicelib/analysis/cktop.c`

**At each GMIN step level change** inside `spice3_gmin()` / `dynamic_gmin()`, emit:

```c
#include "ngspice/diaghooks.h"

/* After each GMIN step attempt (converged or not) */
DIAG_EMIT("{\"hook\":\"gmin\",\"val\":%.6e,\"conv\":%d,\"iters\":%d}\n",
    ckt->CKTdiagGmin,      /* current GMIN value */
    converged,              /* 0 or 1 */
    iteration_count         /* NR iterations used at this GMIN level */
);
```

**At each source stepping level** inside `gillespie_src()`:

```c
DIAG_EMIT("{\"hook\":\"src_step\",\"factor\":%.6e,\"conv\":%d,\"iters\":%d}\n",
    ckt->CKTsrcFact,       /* current source factor (0→1) */
    converged,
    iteration_count
);
```

### AC-5: Hook 4 — Device load values (diode only for now)

**File:** `src/spicelib/devices/dio/dioload.c`

**After computing diode current, conductance, and equivalent current** (after the Shockley evaluation, before matrix stamping), emit:

```c
#include "ngspice/diaghooks.h"

/* After computing cd, gd, but before stamping into MNA matrix */
DIAG_EMIT("{\"hook\":\"device\",\"type\":\"DIO\",\"inst\":\"%s\",\"vd\":%.6e,\"id\":%.6e,\"gd\":%.6e,\"ieq\":%.6e}\n",
    here->DIOname,          /* instance name, e.g., "d1" */
    vd,                     /* diode voltage */
    cd,                     /* diode current */
    gd,                     /* diode conductance (dI/dV) */
    ceq                     /* equivalent current source for NR linearization */
);
```

**Note:** This hook generates one line PER DEVICE PER ITERATION, which can be verbose for circuits with many diodes. Acceptable for diagnostic use — the file is only created when `NGSPICE_DIAG_FILE` is set.

**Future extension (not in this story):** Add similar hooks in `bjtload.c` (gm, gmu, gpi, ic, ib) and `mos1load.c` / `bsim4load.c` (ids, gm, gds, vgs, vds). Start with diode only — it's the simplest device and the most relevant for NodalAI's current convergence failures.

### AC-6: Hook 5 — Matrix condition after LU factorization

**File:** `src/maths/sparse/spfactor.c`

**After LU factorization completes**, emit the min and max diagonal pivot values:

```c
#include "ngspice/diaghooks.h"

/* After spFactor() or spOrderAndFactor() returns */
DIAG_EMIT("{\"hook\":\"matrix\",\"size\":%d,\"min_piv\":%.6e,\"max_piv\":%.6e,\"ratio\":%.6e}\n",
    matrix_size,
    min_pivot,
    max_pivot,
    (min_pivot > 0) ? max_pivot / min_pivot : -1.0
);
```

**Implementation detail:** The min/max pivot values may need to be tracked during the factorization loop. If `spfactor.c` doesn't already track these, add two local variables:

```c
double diag_min_pivot = 1e30, diag_max_pivot = 0.0;

/* Inside the factorization loop, after each pivot selection */
{
    double piv = fabs(pivot_value);
    if (piv < diag_min_pivot) diag_min_pivot = piv;
    if (piv > diag_max_pivot) diag_max_pivot = piv;
}

/* After loop completes */
DIAG_EMIT("{\"hook\":\"matrix\",\"size\":%d,\"min_piv\":%.6e,\"max_piv\":%.6e,\"ratio\":%.6e}\n",
    Size, diag_min_pivot, diag_max_pivot,
    (diag_min_pivot > 0) ? diag_max_pivot / diag_min_pivot : -1.0);
```

### AC-7: Init/close wired into ngspice startup

**File:** `src/main.c` (or the shared library entry point `src/frontend/inppp.c`)

```c
#include "ngspice/diaghooks.h"

/* In main() or the shared library init, near the top */
ngspice_diag_init();

/* At exit / cleanup */
ngspice_diag_close();
```

### AC-8: Zero overhead when disabled

**Given** `NGSPICE_DIAG_FILE` env var is NOT set,
**When** ngspice runs,
**Then**:
- `ngspice_diag_fp` is NULL
- All `DIAG_EMIT()` calls evaluate to `if (NULL) fprintf(...)` which any compiler optimizes to a no-op
- No file I/O occurs
- No measurable performance difference vs unmodified ngspice

### AC-9: Builds without errors

Modified ngspice source compiles cleanly with `make` after adding the hooks. No new dependencies. `diaghooks.h` only requires `<stdio.h>`.

---

## File Summary

| File | Change | Lines Added |
|---|---|---|
| `src/include/ngspice/diaghooks.h` | **NEW** — macro + extern + init/close declarations | ~15 |
| `src/misc/diaghooks.c` | **NEW** — init/close implementation | ~20 |
| `src/maths/ni/niiter.c` | Hook 1 — NR iteration trace in `NIiterate()` | ~3 |
| `src/spicelib/devices/devsup.c` | Hook 2 — Limiter activation in `DEVpnjlim()`, `DEVfetlim()` | ~8 |
| `src/spicelib/analysis/cktop.c` | Hook 3 — GMIN/source step in `spice3_gmin()`, `gillespie_src()` | ~6 |
| `src/spicelib/devices/dio/dioload.c` | Hook 4 — Device values in `DIOload()` | ~3 |
| `src/maths/sparse/spfactor.c` | Hook 5 — Matrix condition after factorization | ~6 |
| `src/main.c` or shared lib entry | Init/close calls | ~2 |
| **Total** | | **~63 lines** |

---

## AI Agent Workflow After Story I

```bash
# 1. Run ngspice with diagnostics on a failing benchmark circuit
NGSPICE_DIAG_FILE=rc_divider.diag.jsonl ngspice -b tests/fixtures/rc_divider.cir

# 2. Run NodalAI on the same circuit (already produces convergence_hints)
python3 -m ecad.cli dc rc_divider.cir --trace

# 3. AI agent compares the two traces:
#    - ngspice: 8 NR iterations, limiter fired twice at V=0.55→0.68V, GMIN=1e-12, condition=4.8e8
#    - NodalAI: 50 NR iterations (max), limiter fired 0 times, no GMIN, condition=2.1e12
#    → Diagnosis: NodalAI's _limit_junction_voltage threshold is too high, and GMIN stepping is missing
```

---

## Test Plan

Testing is done by building the modified ngspice and running a simple circuit:

```bash
# Build modified ngspice
cd Studio-Portable-RAG/Codebase/ngspice
./configure && make

# Test: verify diag file is created when env var is set
NGSPICE_DIAG_FILE=/tmp/test.diag.jsonl ./src/ngspice -b tests/simple_diode.cir
cat /tmp/test.diag.jsonl | python3 -c "import sys,json; [json.loads(l) for l in sys.stdin]; print('VALID JSON Lines')"

# Test: verify no diag file when env var is unset
unset NGSPICE_DIAG_FILE
./src/ngspice -b tests/simple_diode.cir
ls /tmp/test.diag.jsonl  # should not be modified
```

### Validation Checklist

```
Test ID | Description
--------|------------
DH-01   | NGSPICE_DIAG_FILE set → .diag.jsonl created with valid JSON Lines
DH-02   | NGSPICE_DIAG_FILE unset → no file created, no stderr warnings
DH-03   | Hook 1: nr_iter lines present with iter, max_rhs, max_dx, damp, conv fields
DH-04   | Hook 2: limiter lines present when circuit has diodes (vnew_raw != vnew_lim)
DH-05   | Hook 3: gmin lines present when GMIN stepping activates
DH-06   | Hook 4: device lines present with DIO type, vd, id, gd, ieq
DH-07   | Hook 5: matrix lines present with min_piv, max_piv, ratio
DH-08   | All JSON values are finite (no NaN/Inf in output)
DH-09   | Performance: <1% overhead on a 1000-node circuit when disabled
DH-10   | Build: make completes without warnings on the modified source
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Modifying ngspice source creates a fork maintenance burden | Changes are ~63 lines of pure instrumentation, never touching simulation logic. Easy to rebase onto new ngspice releases. |
| Diag file grows large for complex circuits | Only created when `NGSPICE_DIAG_FILE` is explicitly set. For a 76-circuit benchmark, generate one file per circuit. AI agent reads only the failing circuit's trace. |
| Hook 4 (device load) generates many lines per iteration | One line per diode per iteration. For a circuit with 10 diodes and 20 iterations = 200 lines. Acceptable for diagnostic use. |
| Variable names in pseudocode may not match actual C source | Domain docs give the algorithmic structure. Implementor must check actual variable names in the C source. The hook logic is simple enough to adapt. |
| spfactor.c may not have min/max pivot tracking | Add two local `double` variables in the factorization loop. Minimal code change. |

---

## Definition of Done

- [ ] `src/include/ngspice/diaghooks.h` exists with `DIAG_EMIT` macro and `ngspice_diag_fp` extern
- [ ] `src/misc/diaghooks.c` exists with `ngspice_diag_init()` and `ngspice_diag_close()`
- [ ] Hook 1: NR iteration trace in `niiter.c` / `NIiterate()`
- [ ] Hook 2: Limiter activation in `devsup.c` / `DEVpnjlim()` and `DEVfetlim()`
- [ ] Hook 3: GMIN/source stepping in `cktop.c`
- [ ] Hook 4: Diode device values in `dioload.c` / `DIOload()`
- [ ] Hook 5: Matrix condition in `spfactor.c`
- [ ] Init/close wired into ngspice startup/shutdown
- [ ] Builds cleanly with `make`
- [ ] Zero overhead when `NGSPICE_DIAG_FILE` is unset
- [ ] `.diag.jsonl` output is valid JSON Lines parseable by Python
