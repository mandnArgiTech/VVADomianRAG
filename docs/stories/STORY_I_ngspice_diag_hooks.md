# STORY I: ngspice C Diagnostic Instrumentation — AI-Ready Convergence Trace

> **Status:** ✅ DONE — Implemented in the **vendored** ngspice tree under `Studio-Portable-RAG/Codebase/ngspice/`. Story J4 routes hooks via `NgspiceDiagSink` to protobuf `DiagEvent` on PUB. Story L consumes hook data in ConvergenceDiff (confirm L1/L2 ship status separately).

**Repository:** `mandnArgiTech/VVADomianRAG` (vendored ngspice tree at `Studio-Portable-RAG/Codebase/ngspice`, not a submodule)

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

### Activation — file mode

When `NGSPICE_DIAG_FILE` is set, `diaghooks.c` opens `ngspice_diag_fp` and **`ngspice_diag_wants_*()`** returns true for **all** hook types whenever the file is active (no per-hook env filter).

```bash
NGSPICE_DIAG_FILE=circuit.diag.jsonl ngspice -b circuit.cir
```

### Activation — host mode (Story J / zmq_server)

There is **no** `ngspice_diag_zmq_pub` symbol. The shared worker sets:

- **`ngspice_diag_sink`** → `const NgspiceDiagSink *` with callbacks (`on_nr_iter`, `on_limiter_pnj`, `on_limiter_fet`, `on_gmin`, `on_src_step`, `on_device_dio`, `on_matrix`).
- **`ngspice_diag_request_id`** → UTF-8 id for `DiagEvent.request_id` on PUB.

Each **`ngspice_diag_emit_*`** writes JSONL if `ngspice_diag_fp` is set **and** invokes the sink callback if installed. `ngspice-server` wires `server_sink` → `pub_diag()` → protobuf `DiagEvent` on the PUB socket.

### Public API (see `src/include/ngspice/diaghooks.h`)

- `extern FILE *ngspice_diag_fp;`
- `typedef struct NgspiceDiagSink { ... } NgspiceDiagSink;`
- `extern const NgspiceDiagSink *ngspice_diag_sink;`
- `extern const char *ngspice_diag_request_id;`
- `#define DIAG_EMIT(...)` — `fprintf` when file only (legacy); hook sites use **`ngspice_diag_emit_*`**.
- `int ngspice_diag_wants_nr(void);` (and `_matrix`, `_gmin`, `_src`, `_device`, `_pnjlim`, `_fetlim`).
- `void ngspice_diag_emit_nr_iter(int iter, double max_rhs, double max_dx, double damp, int noncon, int converged);` — JSON uses **`conv`** from `converged`; **`noncon`** is passed to the sink only (not duplicated as a JSON field in the `fprintf` format).
- `void ngspice_diag_emit_limiter_pnj(...)`, `ngspice_diag_emit_limiter_fet(...)`, `ngspice_diag_emit_gmin`, `ngspice_diag_emit_src_step`, `ngspice_diag_emit_device_dio`, `ngspice_diag_emit_matrix`.
- `void ngspice_diag_init(void);`, `void ngspice_diag_close(void);`

### Hook Output — JSON Lines (matches `src/misc/diaghooks.c`)

```jsonl
{"hook":"nr_iter","iter":1,"max_rhs":2.3e-1,"max_dx":4.5e-1,"damp":1.0,"conv":0}
{"hook":"limiter","fn":"DEVpnjlim","inst":"","vnew_raw":1.820e+00,"vnew_lim":6.830e-01,"vold":5.510e-01,"vcrit":6.120e-01}
{"hook":"device","type":"DIO","inst":"d1","vd":6.830e-01,"id":2.100e-03,"gd":8.100e-02,"ieq":1.500e-03}
{"hook":"nr_iter","iter":12,"max_rhs":8.2e-13,"max_dx":4.1e-8,"damp":1.0,"conv":1}
{"hook":"gmin","val":1.0e-3,"conv":1,"iters":8}
{"hook":"src_step","factor":1.0e+0,"conv":0,"iters":3}
{"hook":"matrix","size":15,"min_piv":2.3e-6,"max_piv":1.1e+3,"ratio":4.8e+8}
```

**Note:** `DEVpnjlim` / `DEVfetlim` pass **`inst` as `""`** from `devsup.c` today. The **device** hook carries real instance names from `dioload.c`.

**Hook → NodalAI mapping:**

| Hook | ngspice source | NodalAI equivalent |
|---|---|---|
| `nr_iter` | `NIiter()` in `niiter.c` | `_nr_loop()` in `newton_raphson.py` |
| `limiter` | `DEVpnjlim()` in `devsup.c` | `_dev_pnjlim()` in `voltage_limiters.py` |
| `gmin` | `spice3_gmin()` in `cktop.c` | `_gmin_stepping()` in `dc_convergence.py` |
| `src_step` | source stepping in `cktop.c` | `_source_stepping()` in `dc_convergence.py` |
| `device` | `DIOload()` in `dioload.c` | `DiodeModel.evaluate()` in `ecad/devices/diode.py` |
| `matrix` | `spFactor()` in `spfactor.c` | `scipy.linalg.solve()` in `newton_raphson.py` |

---

## Hook 1: NR Iteration Trace — `niiter.c`

After `NIconv()`, before `SWAP(CKTrhs, CKTrhsOld)`, with `diag_nr_have_rhs && ngspice_diag_wants_nr()` and finite checks:

```c
ngspice_diag_emit_nr_iter(iterno, diag_nr_max_rhs, max_dx, diag_nr_damp,
                          ckt->CKTnoncon, conv);
```

(`max_dx` is computed over matrix indices; see `niiter.c`.)

---

## Hook 2: Junction Limiter — `devsup.c`

When `*icheck && ngspice_diag_wants_pnjlim()` and values are finite:

```c
ngspice_diag_emit_limiter_pnj("", vnew_orig, vnew, vold, vcrit);
```

**DEVfetlim:** `ngspice_diag_emit_limiter_fet("", ...)`.

**Critical NodalAI note:** The limiter in NodalAI is gated by `ptc_g < 1e-6` in `newton_raphson.py:1049`. During pseudo-transient continuation (`ptc_g > 0`), the limiter is intentionally disabled — this matches ngspice's design. The bug is the `vcrit_lim = 0.7` fallback at line 1044, not the gate.

---

## Hook 3: GMIN/Source Stepping — `cktop.c`

Emitted via **`ngspice_diag_emit_gmin`** / **`ngspice_diag_emit_src_step`** (see `cktop.c` call sites).

---

## Hook 4: Device Load Values — `dioload.c`

**`ngspice_diag_emit_device_dio(...)`** with real instance name; `cd` is the branch current variable name in ngspice (not `id`).

---

## Hook 5: Matrix Condition — `spfactor.c`

**`ngspice_diag_emit_matrix(...)`** after factorization (see `spfactor.c`).

---

## Build & Test

Hooks ship with **libngspice** built from this tree. Using only a prebuilt `ngspice-server` without rebuilding ngspice does **not** refresh hook call sites.

```bash
cd Studio-Portable-RAG/Codebase/ngspice
make -j$(nproc)

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

unset NGSPICE_DIAG_FILE
./src/ngspice -b ../../DomainDocs/ngspice/test_circuits/simple_diode.cir
```

**CI:** `make test-vidhubijakam-bridge` under `zmq_server/` exercises the **bridge** and ZMQ client paths; it does **not** run `NGSPICE_DIAG_FILE` against CLI `./src/ngspice`.

---

## Story Dependencies

```
Story I (this) ─→ Story J4  (hooks routed to ZMQ PUB socket)
              └─→ Story L1  (NgspiceZMQAdapter reads DiagEvents)
              └─→ Story L2  (ConvergenceDiff interprets hook data → fixes)
```

---

## Known limitations

- **File mode:** all hooks are on when `NGSPICE_DIAG_FILE` is set; no env to enable only NR + limiter.
- **Volume:** unbounded `nr_iter` JSONL lines on large iteration counts; no sampling in Story I scope.
- **Limiter `inst`:** often empty from `devsup.c` until callers pass instance names (future enhancement).
