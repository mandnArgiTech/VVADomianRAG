# STORY I: ngspice C Diagnostic Instrumentation — AI-Ready Convergence Trace

**Repository:** `mandnArgiTech/VVADomianRAG` (ngspice source as git submodule at `Studio-Portable-RAG/Codebase/ngspice`)
**Priority:** High
**Estimated effort:** 4–5 hours
**Files to modify:** 5 ngspice C source files + 1 new header
**Files to create:** `src/include/ngspice/diaghooks.h`, `src/misc/diaghooks.c`

**Reference documents (in this repo):**
- `Studio-Portable-RAG/DomainDocs/ngspice/ngspice_io_dataflow.md` — complete call-stack trace with exact function signatures and variable names
- `Studio-Portable-RAG/DomainDocs/ngspice/ngspice_pageindex.md` — hierarchical source tree index with file→function mapping

**ngspice is now a git submodule** — compiled and buildable locally. The hooks are applied directly to this source tree.

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

**File:** `src/maths/ni/niiter.c`, inside `NIiter()` (confirmed by `ngspice_io_dataflow.md` §6.1)

The NR loop structure (from io_dataflow §6.1):
```c
int NIiter(CKTcircuit *ckt, int maxIter)
{
    for (iterno = 0; iterno < maxIter; iterno++) {
        CKTload(ckt);                    /* stamp all devices */
        SMPluFac(ckt->CKTmatrix, ...);   /* LU factorise */
        SMPsolve(ckt->CKTmatrix, ckt->CKTrhs, ckt->CKTrhsSpare); /* solve */
        if (NIconv(ckt) == OK) return OK;
        SWAP(ckt->CKTrhs, ckt->CKTrhsOld);
    }
    return E_ITERLIM;
}
```

**Insert the hook after `NIconv()` returns and before the `SWAP`:**

```c
#include "ngspice/diaghooks.h"

/* After NIconv check, before SWAP — emit NR iteration state */
{
    /* Compute max |Δx| from CKTrhs vs CKTrhsOld */
    double diag_max_dx = 0.0, diag_max_rhs = 0.0;
    int nn;
    for (nn = 0; nn <= ckt->CKTmaxEqNum; nn++) {
        double dx = fabs(ckt->CKTrhs[nn] - ckt->CKTrhsOld[nn]);
        if (dx > diag_max_dx) diag_max_dx = dx;
    }
    DIAG_EMIT("{\"hook\":\"nr_iter\",\"iter\":%d,\"max_dx\":%.6e,\"noncon\":%d,\"conv\":%d}\n",
        iterno, diag_max_dx, ckt->CKTnoncon, (converged == OK) ? 1 : 0);
}
```

**Key variables (from io_dataflow §10):**
- `ckt->CKTrhs[]` — current solution vector (node voltages + branch currents)
- `ckt->CKTrhsOld[]` — previous iteration solution
- `ckt->CKTnoncon` — nonconvergence counter (set by `NIconv`)
- `ckt->CKTmaxEqNum` — matrix size (number of equations)

### AC-3: Hook 2 — Device limiter activation

**File:** `src/spicelib/devices/devsup.c`, inside `DEVpnjlim()` (confirmed by `ngspice_io_dataflow.md` §6.3 and `ngspice_pageindex.md` §3.3)

The io_dataflow (§6.3) shows the limiter call in context:
```
DIOload → DEVpnjlim(vd, &vd, vt, here->DIOtSatCur, …)
  "if (vd > vcrit) vd = vdold + Vt * log(1 + (vd - vdold)/Vt)"
```

**Save original vnew at function entry, emit when limiting occurs:**

```c
#include "ngspice/diaghooks.h"

double DEVpnjlim(double vnew, double vold, double vt, double vcrit, int *icheck)
{
    double vnew_orig = vnew;  /* ← ADD: save before any modification */
    double arg;

    /* ... existing limiting logic (unchanged) ... */

    /* ADD at end, just before return: emit only when limiting fired */
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

**File:** `src/spicelib/analysis/cktop.c` (confirmed by `ngspice_io_dataflow.md` §5.2 and `ngspice_pageindex.md` §3.2)

The io_dataflow (§5.2) shows the convergence aid flow:
```
DCop() → NIiter() → if not converged → niniter.c (source stepping / GMIN stepping)
```

**Key variables (from io_dataflow §10):**
- `ckt->CKTgmin` — current GMIN value (the diagonal conductance added for conditioning)
- `ckt->CKTsrcFact` — source stepping factor (0→1 during homotopy, not present in all versions — check actual source)

**At each GMIN step level change** inside the GMIN stepping function:

```c
#include "ngspice/diaghooks.h"

/* After each GMIN step attempt */
DIAG_EMIT("{\"hook\":\"gmin\",\"val\":%.6e,\"conv\":%d,\"iters\":%d}\n",
    ckt->CKTgmin,           /* current GMIN value */
    converged,              /* 0 or 1 */
    iteration_count         /* NR iterations used at this GMIN level */
);
```

**Note:** The GMIN stepping function may be named `spice3_gmin()`, `dynamic_gmin()`, or be inline in `cktop.c` — the implementor should search for `CKTdiagGmin` or `CKTgmin` assignments in `cktop.c` and `niniter.c`. The io_dataflow confirms the convergence aid sequence: GMIN stepping first, source stepping as fallback (§5.2).

**At each source stepping level** (if `gillespie_src()` or equivalent exists):

```c
DIAG_EMIT("{\"hook\":\"src_step\",\"factor\":%.6e,\"conv\":%d,\"iters\":%d}\n",
    src_factor,             /* current source factor (0→1) */
    converged,
    iteration_count
);
```

### AC-5: Hook 4 — Device load values (diode only for now)

**File:** `src/spicelib/devices/dio/dioload.c` (confirmed by `ngspice_io_dataflow.md` §6.3 and `ngspice_pageindex.md` §3.3)

The io_dataflow (§6.3) traces the exact DIOload sequence:
```
DIOload(DIOinstance *here, CKTcircuit *ckt)
  ├─ vd = CKTrhs[here->DIOposNode] - CKTrhs[here->DIOnegNode]
  ├─ DEVpnjlim(vd, &vd, vt, …)          ← voltage limiter
  ├─ id = IS * (exp(vd / (N * Vt)) - 1) ← Shockley equation
  ├─ gd = ∂id/∂vd = IS/(N*Vt) * exp(…)  ← conductance
  ├─ SMPaddElement(…, gd + Gcond)         ← matrix stamp
  └─ CKTrhs[node] -= (id - gd*vd)        ← Norton RHS (ieq = id - gd*vd)
```

**After computing cd (diode current), gd (conductance), and before matrix stamping:**

```c
#include "ngspice/diaghooks.h"

/* After Shockley evaluation, before SMPaddElement stamps */
DIAG_EMIT("{\"hook\":\"device\",\"type\":\"DIO\",\"inst\":\"%s\",\"vd\":%.6e,\"id\":%.6e,\"gd\":%.6e,\"ieq\":%.6e}\n",
    here->DIOname,     /* instance name, e.g., "d1" (from CKT node table) */
    vd,                /* diode voltage */
    cd,                /* diode current (variable name in dioload.c) */
    gd,                /* diode conductance dI/dV */
    (cd - gd * vd)     /* Norton equivalent current (ieq) */
);
```

**Note on variable names:** The io_dataflow uses `id` for current but the actual `dioload.c` uses `cd`. Both are visible in the RAG retrieval of the DIOload function — the implementor should check the actual local variable name.

**Future extension (not in this story):** Add similar hooks in:
- `bjtload.c` — emit `gm`, `gmu`, `gpi`, `ic`, `ib` (see `ngspice_pageindex.md` §3.3 BJT entry)
- `mos1load.c` / `bsim4v7/b4v7ld.c` — emit `ids`, `gm`, `gds`, `vgs`, `vds`

Start with diode only — it's the simplest device and the most relevant for NodalAI's current convergence failures on the 76-circuit benchmark.

### AC-6: Hook 5 — Matrix condition after LU factorization

**File:** `src/maths/sparse/spfactor.c` (confirmed by `ngspice_pageindex.md` §4.2)

The io_dataflow (§6.1) shows:
```
NIiter loop:
  SMPluFac(ckt->CKTmatrix, ckt->CKTpivotRelTol, ckt->CKTpivotAbsTol)
```

The pageindex (§4.2) confirms: "Key functions: `SMPpreOrder()`, `SMPluFac()`, `SMPsolve()`, `SMPclear()`"

**After LU factorization completes in `spFactor()` or `spOrderAndFactor()`**, emit the min and max diagonal pivot values:

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

**File:** `src/main.c` (confirmed by `ngspice_io_dataflow.md` §9: `main() [src/frontend/main.c]`)

For batch mode (`ngspice -b circuit.cir`), the call stack is:
```
main() → ft_doreadcir() → ... → IFrunAnalysis()
```

For shared library mode, the entry point is the `ngSpice_Init()` export.

```c
#include "ngspice/diaghooks.h"

/* In main(), near the top after command-line parsing */
ngspice_diag_init();

/* At exit / cleanup (or register via atexit()) */
atexit(ngspice_diag_close);
```

**Alternative:** If modifying `main.c` is too invasive (it's in `src/frontend/` which is outside the core spicelib), put the init in `CKTsetup()` (`src/spicelib/analysis/cktsetup.c`) — this is called once before any analysis runs (confirmed by io_dataflow §4.1). And put the close in `OUTendPlot()` (`src/frontend/outitf.c`) which runs after every analysis completes (io_dataflow §7.3).

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

All paths relative to `Studio-Portable-RAG/Codebase/ngspice/` (the git submodule):

| File | Change | Lines Added |
|---|---|---|
| `src/include/ngspice/diaghooks.h` | **NEW** — macro + extern + init/close declarations | ~15 |
| `src/misc/diaghooks.c` | **NEW** — init/close implementation | ~20 |
| `src/maths/ni/niiter.c` | Hook 1 — NR iteration trace after `NIconv()` in `NIiter()` loop | ~8 |
| `src/spicelib/devices/devsup.c` | Hook 2 — Limiter activation at end of `DEVpnjlim()` and `DEVfetlim()` | ~8 |
| `src/spicelib/analysis/cktop.c` | Hook 3 — GMIN/source step after each homotopy level attempt | ~6 |
| `src/spicelib/devices/dio/dioload.c` | Hook 4 — Device values after Shockley eval, before `SMPaddElement` stamps | ~3 |
| `src/maths/sparse/spfactor.c` | Hook 5 — Min/max pivot after LU factorization in `spFactor()` | ~6 |
| `src/frontend/main.c` (or `src/spicelib/analysis/cktsetup.c`) | `ngspice_diag_init()` call | ~1 |
| `src/frontend/main.c` (or via `atexit()`) | `ngspice_diag_close()` call | ~1 |
| **Total** | | **~68 lines** |

## Build & Test

Since ngspice is now a local submodule:

```bash
cd Studio-Portable-RAG/Codebase/ngspice

# If not yet configured:
./autogen.sh   # (or ./configure if autogen already ran)
./configure --prefix=$PWD/install --enable-xspice --disable-debug

# Build with hooks:
make -j$(nproc)

# Test: verify diag file is created
NGSPICE_DIAG_FILE=/tmp/test.diag.jsonl ./src/ngspice -b ../../examples/simple_diode.cir
cat /tmp/test.diag.jsonl | python3 -c "import sys,json; lines=[json.loads(l) for l in sys.stdin]; print(f'VALID: {len(lines)} diagnostic lines')"

# Test: verify no diag file when env var is unset
unset NGSPICE_DIAG_FILE
./src/ngspice -b ../../examples/simple_diode.cir
# No /tmp/test.diag.jsonl modification
```

---

## AI Agent Workflow After Story I

```bash
# 1. Run ngspice (from the submodule) with diagnostics on a failing benchmark circuit
NGSPICE_DIAG_FILE=rc_divider.diag.jsonl \
  Studio-Portable-RAG/Codebase/ngspice/src/ngspice -b tests/fixtures/rc_divider.cir

# 2. Run NodalAI on the same circuit (already produces convergence_hints)
python3 -m ecad.cli dc rc_divider.cir --trace

# 3. AI agent (Cursor) reads both traces via MCP + RAG:
#    - ngspice trace: 8 NR iterations, limiter fired twice (V=0.55→0.68V),
#      GMIN=1e-12, matrix condition=4.8e8
#    - NodalAI trace: 50 iterations (max_iter hit), limiter fired 0 times,
#      no GMIN stepping, matrix condition=2.1e12
#    → Diagnosis: NodalAI's _limit_junction_voltage threshold is too high,
#      and GMIN stepping is missing from the convergence aid sequence
```

## Cross-Reference with RAG

The diagnostic hooks produce the **runtime numerical data**. The RAG provides the **code and algorithmic context**. Together:

| Question the AI Agent Asks | Data Source |
|---|---|
| "What voltage did ngspice clamp to?" | `.diag.jsonl` → `limiter` hook: `vnew_lim` |
| "How does the limiter algorithm work?" | RAG → `devsup.c` chunk + Chapter_05 domain doc |
| "How many NR iterations did ngspice need?" | `.diag.jsonl` → `nr_iter` hook: final `iter` count |
| "What convergence tolerance was used?" | RAG → `cktdefs.h` chunk: `CKTvntol`, `CKTreltol` + io_dataflow §12 |
| "Was the matrix ill-conditioned?" | `.diag.jsonl` → `matrix` hook: `ratio` |
| "What does ngspice do when the matrix is singular?" | RAG → Chapter_06 domain doc: GMIN stepping, source stepping |

---

## Test Plan

Testing is done by building the modified ngspice submodule and running a simple circuit:

```bash
cd Studio-Portable-RAG/Codebase/ngspice

# Build (assumes ./configure already ran)
make -j$(nproc)

# Test 1: verify diag file is created when env var is set
NGSPICE_DIAG_FILE=/tmp/test.diag.jsonl ./src/ngspice -b ../../DomainDocs/ngspice/test_circuits/simple_diode.cir
# (or use any .cir file with a diode: V1 in 0 5 / R1 in out 1k / D1 out 0 D1N4148 / .model D1N4148 D / .op / .end)
python3 -c "import sys,json; [json.loads(l) for l in open('/tmp/test.diag.jsonl')]; print('VALID JSON Lines')"

# Test 2: verify no diag file when env var is unset
unset NGSPICE_DIAG_FILE
./src/ngspice -b ../../DomainDocs/ngspice/test_circuits/simple_diode.cir
# /tmp/test.diag.jsonl should NOT be modified

# Test 3: verify hooks present in a real simulation
NGSPICE_DIAG_FILE=/tmp/test.diag.jsonl ./src/ngspice -b ../../DomainDocs/ngspice/test_circuits/simple_diode.cir
python3 -c "
import json
hooks = {}
for line in open('/tmp/test.diag.jsonl'):
    d = json.loads(line)
    hooks.setdefault(d['hook'], 0)
    hooks[d['hook']] += 1
print('Hooks found:', hooks)
assert 'nr_iter' in hooks, 'Missing NR iteration hook'
assert 'device' in hooks, 'Missing device hook'
print('ALL HOOKS PRESENT')
"
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
