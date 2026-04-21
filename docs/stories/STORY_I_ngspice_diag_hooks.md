# STORY I: ngspice C Diagnostic Instrumentation — AI-Ready Convergence Trace

> **Status:** ✅ DONE — Applied to ngspice submodule (commit `2af7692`). Story J4 routes hooks to ZMQ PUB. Story L consumes hook data in ConvergenceDiff.

**Repository:** `mandnArgiTech/VVADomianRAG` (ngspice submodule at `Studio-Portable-RAG/Codebase/ngspice`)
**Files created:** `src/include/ngspice/diaghooks.h`, `src/misc/diaghooks.c`
**Files modified:** `src/maths/ni/niiter.c`, `src/spicelib/devices/devsup.c`, `src/spicelib/analysis/cktop.c`, `src/spicelib/devices/dio/dioload.c`, `src/maths/sparse/spfactor.c`, `src/main.c`, `src/sharedspice.c`, `src/misc/Makefile.am`

---

## Mission: ngspice as AI-Ready Reference Oracle

The strategic goal is not to run ngspice in a browser or replace it with Python. It is to make ngspice **AI-readable at runtime** — so that an AI agent (Cursor + VVADomainRAG RAG) can observe exactly how ngspice converges on a circuit, then translate that observation into targeted fixes for NodalAI's Python MNA solver.

**Why this matters concretely:**

NodalAI's DC OP convergence sequence (`ecad/mna/dc_convergence.py`) is:
1. Standard NR (`_nr_loop`, up to `max_iter=200`)
2. GMIN stepping (`_gmin_stepping`)
3. Source stepping (`_source_stepping`)
4. Pseudo-transient continuation (`_pseudotransient_continuation`)

When NodalAI fails on step 1 and ngspice converges in 12 iterations, the AI agent needs to know: did ngspice use its limiter? How many times? At what voltage? Did GMIN stepping fire? Without Story I hooks, the agent reads source code and guesses. With hooks, it reads the runtime trace and knows.

**Confirmed real bug found via this approach:** `newton_raphson.py:1044` has `vcrit_lim = 0.7` as a hardcoded fallback for the junction voltage limiter. The correct IS-dependent formula `vcrit = N_VT * log(N_VT / (sqrt(2) * IS))` is computed in `ecad/devices/diode.py:59` and stored on `DiodeModel.vcrit`. But if `device_cache.get(c["id"])` returns `None` (cache miss), the fallback `0.7` is used — making the limiter too permissive for high-IS diodes and too restrictive for low-IS diodes. Story I's `limiter` hook exposes this mismatch directly.

---

## Architecture

### Activation

**File mode:**
```bash
NGSPICE_DIAG_FILE=circuit.diag.jsonl ngspice -b circuit.cir
```

**Socket mode (Story J4):**
`ngspice_diag_zmq_pub != NULL` → hooks emit protobuf DiagEvent to ZMQ PUB socket instead of file. Both modes can coexist for server debugging.

### Hook Output — JSON Lines

```jsonl
{"hook":"nr_iter","iter":1,"max_rhs":2.3e-1,"max_dx":4.5e-1,"damp":1.0,"conv":0}
{"hook":"limiter","fn":"DEVpnjlim","vnew_raw":1.820,"vnew_lim":0.683,"vold":0.551,"vcrit":0.612}
{"hook":"device","type":"DIO","inst":"d1","vd":0.683,"id":2.1e-3,"gd":8.1e-2,"ieq":1.5e-3}
{"hook":"nr_iter","iter":12,"max_rhs":8.2e-13,"max_dx":4.1e-8,"damp":1.0,"conv":1}
{"hook":"gmin","val":1.0e-3,"conv":1,"iters":8}
{"hook":"matrix","size":15,"min_piv":2.3e-6,"max_piv":1.1e+3,"ratio":4.8e+8}
```

**Hook → NodalAI mapping:**

| Hook | ngspice source | NodalAI equivalent |
|---|---|---|
| `nr_iter` | `NIiter()` in `niiter.c` | `_nr_loop()` in `newton_raphson.py` |
| `limiter` | `DEVpnjlim()` in `devsup.c` | `_dev_pnjlim()` in `voltage_limiters.py` |
| `gmin` | `spice3_gmin()` in `cktop.c` | `_gmin_stepping()` in `dc_convergence.py` |
| `src_step` | source stepping in `cktop.c` | `_source_stepping()` in `dc_convergence.py` |
| `device` | `DIOload()` in `dioload.c` | `DiodeModel.evaluate()` in `ecad/devices/diode.py` |
| `matrix` | `spFactor()` in `spfactor.c` | `scipy.linalg.solve()` in `newton_raphson.py` |

### Macro

```c
/* src/include/ngspice/diaghooks.h */
extern FILE *ngspice_diag_fp;
extern void *ngspice_diag_zmq_pub;

#define DIAG_EMIT(...) \
    do { if (ngspice_diag_fp) fprintf(ngspice_diag_fp, __VA_ARGS__); } while (0)

void ngspice_diag_init(void);
void ngspice_diag_close(void);
```

---

## Hook 1: NR Iteration Trace — `niiter.c`

After `NIconv()`, before `SWAP(CKTrhs, CKTrhsOld)` in `NIiter()`:

```c
double diag_max_dx = 0.0;
for (int nn = 0; nn <= ckt->CKTmaxEqNum; nn++) {
    double dx = fabs(ckt->CKTrhs[nn] - ckt->CKTrhsOld[nn]);
    if (dx > diag_max_dx) diag_max_dx = dx;
}
DIAG_EMIT("{\"hook\":\"nr_iter\",\"iter\":%d,\"max_rhs\":%.6e,\"max_dx\":%.6e,\"damp\":%.6e,\"conv\":%d}\n",
    iterno, diag_max_dx, diag_max_dx, 1.0, (converged == OK) ? 1 : 0);
```

---

## Hook 2: Junction Limiter — `devsup.c`

In `DEVpnjlim()`, save `vnew` at entry, emit only when `*icheck = 1`:

```c
double vnew_orig = vnew;  /* ADD AT FUNCTION TOP */
/* ... existing logic ... */
if (*icheck) {
    DIAG_EMIT("{\"hook\":\"limiter\",\"fn\":\"DEVpnjlim\",\"vnew_raw\":%.6e,\"vnew_lim\":%.6e,\"vold\":%.6e,\"vcrit\":%.6e}\n",
        vnew_orig, vnew, vold, vcrit);
}
```

Same pattern for `DEVfetlim()`.

**Critical NodalAI note:** The limiter in NodalAI is gated by `ptc_g < 1e-6` in `newton_raphson.py:1049`. During pseudo-transient continuation (`ptc_g > 0`), the limiter is intentionally disabled — this matches ngspice's design. The bug is the `vcrit_lim = 0.7` fallback at line 1044, not the gate.

---

## Hook 3: GMIN/Source Stepping — `cktop.c`

After each convergence level attempt:

```c
DIAG_EMIT("{\"hook\":\"gmin\",\"val\":%.6e,\"conv\":%d,\"iters\":%d}\n",
    ckt->CKTgmin, converged, iteration_count);

DIAG_EMIT("{\"hook\":\"src_step\",\"factor\":%.6e,\"conv\":%d,\"iters\":%d}\n",
    src_factor, converged, iteration_count);
```

---

## Hook 4: Device Load Values — `dioload.c`

After Shockley evaluation, before `SMPaddElement`. Variable name is `cd` (not `id`) in ngspice:

```c
DIAG_EMIT("{\"hook\":\"device\",\"type\":\"DIO\",\"inst\":\"%s\",\"vd\":%.6e,\"id\":%.6e,\"gd\":%.6e,\"ieq\":%.6e}\n",
    here->DIOname, vd, cd, gd, cd - gd * vd);
```

---

## Hook 5: Matrix Condition — `spfactor.c`

After LU factorization via `diag_emit_matrix_factored()` helper:

```c
void diag_emit_matrix_factored(MatrixPtr Matrix) {
    double min_piv = 1e308, max_piv = 0.0;
    for (int i = 1; i <= Matrix->Size; i++) {
        double piv = fabs(Matrix->Diag[i]->Real);
        if (piv > 0 && piv < min_piv) min_piv = piv;
        if (piv > max_piv) max_piv = piv;
    }
    DIAG_EMIT("{\"hook\":\"matrix\",\"size\":%d,\"min_piv\":%.6e,\"max_piv\":%.6e,\"ratio\":%.6e}\n",
        Matrix->Size, min_piv, max_piv,
        (min_piv > 0) ? max_piv / min_piv : 1e308);
}
```

---

## Build & Test

```bash
cd Studio-Portable-RAG/Codebase/ngspice
make -j$(nproc)

# File mode test
NGSPICE_DIAG_FILE=/tmp/test.diag.jsonl \
  ./src/ngspice -b ../../DomainDocs/ngspice/test_circuits/simple_diode.cir

python3 -c "
import json
lines = [json.loads(l) for l in open('/tmp/test.diag.jsonl')]
hooks = {d['hook'] for d in lines}
print('Hooks found:', hooks)
assert 'nr_iter' in hooks, 'Missing NR hook'
assert 'limiter' in hooks, 'Missing limiter hook'
assert 'device' in hooks, 'Missing device hook'
print('PASS')
"

# Zero-overhead test (no env var)
unset NGSPICE_DIAG_FILE
./src/ngspice -b ../../DomainDocs/ngspice/test_circuits/simple_diode.cir
```

## Story Dependencies

```
Story I (this) ─→ Story J4  (hooks routed to ZMQ PUB socket)
              └─→ Story L1  (NgspiceZMQAdapter reads DiagEvents)
              └─→ Story L2  (ConvergenceDiff interprets hook data → fixes)
```
