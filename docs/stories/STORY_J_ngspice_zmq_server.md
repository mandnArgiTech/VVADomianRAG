# STORY J: ngspice Socket Server with ZMQ + Protobuf

> **This is a multi-part story.** Each sub-story (J1–J6) is independently implementable and testable. Implement in order — each builds on the previous.

**Repository:** `mandnArgiTech/VVADomianRAG` (vendored ngspice tree at `Studio-Portable-RAG/Codebase/ngspice`, not a submodule)
**Priority:** Medium (after Story I file-based hooks are validated)
**Total estimated effort:** 12–16 hours across 6 sub-stories

**Reference documents:**
- `Studio-Portable-RAG/DomainDocs/ngspice/ngspice_io_dataflow.md` — complete call-stack and data structures
- `Studio-Portable-RAG/DomainDocs/ngspice/ngspice_pageindex.md` — source tree index
- `docs/stories/STORY_I_ngspice_diag_hooks.md` — the 5 hook points this story builds on

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────┐
│  ngspice server  (persistent C process)              │
│                                                      │
│  ┌─────────────────┐    ┌──────────────────────┐     │
│  │ ZMQ REP :5555   │    │ ZMQ PUB :5556        │     │
│  │ SimRequest →    │    │ → DiagEvent stream   │     │
│  │ ← SimResult    │    │   (nr_iter, limiter,  │     │
│  └────────┬────────┘    │    device, gmin,      │     │
│           │             │    matrix)            │     │
│           ▼             └──────────┬───────────┘     │
│  ┌─────────────────┐              │                  │
│  │ Simulation Core │──────────────┘                  │
│  │ CKTcircuit pool │  hooks emit to PUB socket      │
│  │ (reusable)      │  instead of fprintf             │
│  └─────────────────┘                                 │
└──────────────────────────────────────────────────────┘
         │ protobuf               │ protobuf
         ▼                        ▼
┌──────────────┐         ┌──────────────────┐
│ Python       │         │ Any consumer:    │
│ client lib   │         │ NodalAI, RAG,    │
│ (ngspice_    │         │ dashboard, CLI   │
│  client.py)  │         │                  │
└──────────────┘         └──────────────────┘
```

---

# STORY J1: Protobuf Schema Definition

**Estimated effort:** 1–2 hours
**Files to create:** `proto/ngspice_sim.proto`, `proto/Makefile`
**Dependencies:** `protoc` compiler, `protobuf-c` (for C) or `nanopb` (lightweight embedded-friendly)

## Business Context

Define the wire format once — all subsequent stories use the generated C structs and Python classes. Getting the schema right first means no rework later.

## Acceptance Criteria

### AC-1: Proto file with all message types

**Given** `proto/ngspice_sim.proto`,
**When** compiled with `protoc`,
**Then** it generates C and Python bindings for:

```protobuf
syntax = "proto3";
package ngspice;

// ─── Client → Server ───

message SimRequest {
  string netlist = 1;                    // full .cir content as string
  string analysis = 2;                   // "op", "dc", "tran", "ac"
  map<string, double> options = 3;       // VNTOL, RELTOL, GMIN overrides
  bool stream_diagnostics = 4;           // enable hook streaming on PUB socket
  string request_id = 5;                 // caller-assigned ID for correlation
}

// ─── Server → Client (reply) ───

message SimResult {
  string request_id = 1;
  bool converged = 2;
  int32 iterations = 3;
  map<string, double> node_voltages = 4;
  map<string, double> branch_currents = 5;
  repeated string warnings = 6;
  double wall_time_ms = 7;              // simulation wall-clock time
  ErrorCode error = 8;

  enum ErrorCode {
    OK = 0;
    PARSE_ERROR = 1;
    CONVERGENCE_FAILURE = 2;
    SINGULAR_MATRIX = 3;
    INTERNAL_ERROR = 4;
    TIMEOUT = 5;
  }
}

// ─── Diagnostic stream (PUB socket) ───

message DiagEvent {
  string request_id = 1;                // correlate with SimRequest
  int64 timestamp_us = 2;               // microseconds since sim start

  oneof event {
    NRIteration nr_iter = 10;
    LimiterActivation limiter = 11;
    GminStep gmin = 12;
    SourceStep src_step = 13;
    DeviceLoad device = 14;
    MatrixCondition matrix = 15;
  }
}

message NRIteration {
  int32 iter = 1;
  double max_dx = 2;                    // max |V_new - V_old| across nodes
  int32 noncon = 3;                     // non-convergence count from NIconv
  bool converged = 4;
}

message LimiterActivation {
  string function = 1;                  // "DEVpnjlim" or "DEVfetlim"
  string instance = 2;                  // device instance name if available
  double vnew_raw = 3;                  // voltage before limiting
  double vnew_limited = 4;              // voltage after limiting
  double vold = 5;                      // previous iteration voltage
  double vcrit = 6;                     // critical voltage threshold
}

message GminStep {
  double value = 1;                     // current GMIN conductance
  bool converged = 2;
  int32 iterations = 3;                 // NR iterations at this GMIN level
}

message SourceStep {
  double factor = 1;                    // source stepping factor (0→1)
  bool converged = 2;
  int32 iterations = 3;
}

message DeviceLoad {
  string type = 1;                      // "DIO", "BJT", "MOS", "JFET"
  string instance = 2;                  // instance name e.g. "d1"
  map<string, double> values = 3;       // flexible: {vd, id, gd, ieq} or {vgs, ids, gm, gds}
}

message MatrixCondition {
  int32 size = 1;                       // number of equations
  double min_pivot = 2;
  double max_pivot = 3;
  double condition_ratio = 4;           // max/min (higher = worse)
}
```

### AC-2: Makefile generates C and Python

```makefile
# proto/Makefile
PROTO_SRC = ngspice_sim.proto

# C generation (using protobuf-c)
c: $(PROTO_SRC)
	protoc-c --c_out=../src/include/ngspice/ $(PROTO_SRC)

# Python generation
py: $(PROTO_SRC)
	protoc --python_out=../python/ $(PROTO_SRC)

all: c py
```

### AC-3: Generated files compile and import

```bash
# C: generated header compiles without errors
cd src/include/ngspice && gcc -c ngspice_sim.pb-c.c -I.

# Python: generated module imports
cd python && python3 -c "from ngspice_sim_pb2 import SimRequest, SimResult, DiagEvent; print('OK')"
```

## Test Plan

```
Test ID | Description
--------|------------
J1-01   | protoc compiles ngspice_sim.proto without errors
J1-02   | C header includes and compiles in a test .c file
J1-03   | Python import of generated _pb2 module succeeds
J1-04   | SimRequest can be serialized and deserialized in Python
J1-05   | DiagEvent with NRIteration oneof round-trips correctly
J1-06   | DeviceLoad.values map serializes {vd, id, gd, ieq} correctly
```

## Definition of Done

- [ ] `proto/ngspice_sim.proto` exists with all message types
- [ ] `proto/Makefile` generates C and Python bindings
- [ ] Generated C header compiles
- [ ] Generated Python module imports
- [ ] Round-trip serialization test passes

---

# STORY J2: ZMQ Server Shell in C

**Estimated effort:** 2–3 hours
**Files to create:** `src/server/ngspice_server.c`, `src/server/ngspice_server.h`
**Dependencies:** `libzmq` (via system package `libzmq3-dev` on Ubuntu)

## Business Context

Build the network shell — a C program that binds REP and PUB sockets, receives protobuf messages, and replies with dummy results. No simulation logic yet — just the socket plumbing.

## Acceptance Criteria

### AC-1: Server binary builds

A new build target `ngspice-server` that compiles and links against `libzmq` and `protobuf-c`.

### AC-2: REP socket accepts SimRequest, replies SimResult

```c
// Pseudocode for the server loop
void *ctx = zmq_ctx_new();
void *rep = zmq_socket(ctx, ZMQ_REP);
zmq_bind(rep, "tcp://*:5555");

while (1) {
    zmq_msg_t msg;
    zmq_msg_init(&msg);
    zmq_msg_recv(&msg, rep, 0);

    // Deserialize SimRequest
    SimRequest *req = sim_request__unpack(NULL, zmq_msg_size(&msg), zmq_msg_data(&msg));

    // (J3 will add actual simulation here)
    // For now: echo back a dummy SimResult
    SimResult result = SIM_RESULT__INIT;
    result.request_id = req->request_id;
    result.converged = true;
    result.iterations = 0;

    // Serialize and send reply
    size_t len = sim_result__get_packed_size(&result);
    uint8_t *buf = malloc(len);
    sim_result__pack(&result, buf);
    zmq_send(rep, buf, len, 0);

    free(buf);
    sim_request__free_unpacked(req, NULL);
    zmq_msg_close(&msg);
}
```

### AC-3: PUB socket binds and is ready for diagnostic streaming

```c
void *pub = zmq_socket(ctx, ZMQ_PUB);
zmq_bind(pub, "tcp://*:5556");
// Hooks (J4) will publish DiagEvent messages to this socket
```

### AC-4: Graceful shutdown on SIGINT/SIGTERM

Server catches signals, closes sockets, destroys context, exits cleanly.

### AC-5: Command-line options

```bash
ngspice-server [--rep-port 5555] [--pub-port 5556] [--bind-addr tcp://*]
```

## Test Plan

```
Test ID | Description
--------|------------
J2-01   | ngspice-server binary builds without errors
J2-02   | Server starts, binds ports, prints "listening on tcp://*:5555"
J2-03   | Python client sends SimRequest, receives SimResult with matching request_id
J2-04   | Server handles 100 sequential requests without crash
J2-05   | SIGINT causes clean shutdown (no socket leak, no crash)
J2-06   | PUB socket binds successfully on :5556
```

## Definition of Done

- [ ] `ngspice-server` binary builds and runs
- [ ] REP socket accepts and replies protobuf messages
- [ ] PUB socket binds for diagnostic streaming
- [ ] Clean signal handling
- [ ] Python client can round-trip a SimRequest → SimResult

---

# STORY J3: Wire SimRequest to ngspice Simulation Core

**Estimated effort:** 3–4 hours
**Files to modify:** `src/server/ngspice_server.c`
**Dependencies:** Story J2 (server shell), Story I (hook points)

## Business Context

Connect the socket server to ngspice's actual simulation engine. When a SimRequest arrives with a netlist string, parse it, run the analysis, and return real node voltages in SimResult.

## Acceptance Criteria

### AC-1: Netlist string → CKTcircuit

Use ngspice's internal API to parse the netlist from the SimRequest string (not from disk):

```c
// Convert netlist string to struct line deck (in-memory, no file I/O)
struct line *deck = inp_readall_from_string(req->netlist);
// Or: write to a tmpfile and call inp_readall() — simpler but slower

// Parse the deck
INPpas1(ckt, deck, tab);
INPpas2(ckt, deck, tab, nodTab);

// Setup
CKTsetup(ckt);
CKTtemp(ckt);
```

Refer to `ngspice_io_dataflow.md` §2–4 for the exact call sequence.

### AC-2: Run analysis, collect results

```c
// Run DC operating point (most common for NodalAI comparison)
DCop(ckt);

// Extract node voltages into SimResult.node_voltages map
for (node = ckt->CKTnodeTab; node; node = node->next) {
    // result.node_voltages[node->name] = ckt->CKTrhs[node->index]
}
```

Refer to `ngspice_io_dataflow.md` §5.2 for DCop flow.

### AC-3: SimResult populated with real data

The returned SimResult must contain:
- `converged`: true/false based on NIiter return code
- `iterations`: actual NR iteration count
- `node_voltages`: map of node name → voltage value
- `branch_currents`: map of voltage source name → branch current
- `wall_time_ms`: actual simulation time
- `error`: appropriate ErrorCode if simulation failed

### AC-4: Handle parse errors gracefully

If the netlist has syntax errors, return `SimResult` with `error = PARSE_ERROR` and the error message in `warnings[]`. Do NOT crash the server.

### AC-5: Handle convergence failure gracefully

If NIiter returns `E_ITERLIM`, return `SimResult` with `error = CONVERGENCE_FAILURE`, `converged = false`, and partial node voltages (the last NR iteration values).

### AC-6: CKTcircuit cleanup between requests

After each simulation, free the CKT struct and all device instances. The server must handle unlimited sequential requests without memory leaks.

```c
CKTdestroy(ckt);  // free everything
```

## Test Plan

```
Test ID | Description
--------|------------
J3-01   | Send simple resistor divider netlist → correct node voltages returned
J3-02   | Send diode circuit → converged=true, correct Vd ≈ 0.65V
J3-03   | Send invalid netlist → error=PARSE_ERROR, server still alive
J3-04   | Send circuit that doesn't converge → error=CONVERGENCE_FAILURE, partial voltages
J3-05   | Send 100 different circuits sequentially → no memory leak (RSS stable)
J3-06   | wall_time_ms is non-zero and reasonable
J3-07   | node_voltages map has correct node names (not just indices)
J3-08   | branch_currents has voltage source currents
```

## Definition of Done

- [ ] SimRequest with netlist string triggers actual ngspice simulation
- [ ] SimResult contains real node voltages and branch currents
- [ ] Parse errors and convergence failures handled gracefully
- [ ] No memory leaks across sequential requests
- [ ] Simple diode circuit returns correct Vd

---

# STORY J4: Route Diagnostic Hooks to PUB Socket

**Estimated effort:** 2–3 hours
**Files to modify:** `src/include/ngspice/diaghooks.h`, `src/misc/diaghooks.c`, the 5 hook files from Story I
**Dependencies:** Story J2 (PUB socket), Story I (hook points)

## Business Context

Story I adds **call sites** in ngspice C. `src/misc/diaghooks.c` implements **`ngspice_diag_emit_*`**: each path writes JSON Lines when `NGSPICE_DIAG_FILE` / `ngspice_diag_fp` is set, and invokes **`NgspiceDiagSink`** callbacks when `ngspice_diag_sink` is non-NULL. **`ngspice-server`** (`zmq_server/ngspice_server.c`) installs **`server_sink`** on workers so callbacks build protobuf **`DiagEvent`** and forward to the master for the **PUB** socket (`pub_diag`). There is **no** `ngspice_diag_zmq_pub`; ZMQ publishing lives entirely in the server process.

## Acceptance Criteria (as shipped)

### AC-1: Public API (`diaghooks.h` / `diaghooks.c`)

- `NgspiceDiagSink` with typed callbacks (`on_nr_iter`, `on_limiter_pnj`, `on_limiter_fet`, `on_gmin`, `on_src_step`, `on_device_dio`, `on_matrix`).
- `ngspice_diag_sink`, `ngspice_diag_request_id`, `ngspice_diag_fp`.
- `ngspice_diag_wants_*()` gates hot paths before expensive work.
- `ngspice_diag_emit_nr_iter`, `ngspice_diag_emit_limiter_pnj`, `ngspice_diag_emit_limiter_fet`, `ngspice_diag_emit_gmin`, `ngspice_diag_emit_src_step`, `ngspice_diag_emit_device_dio`, `ngspice_diag_emit_matrix`.

`DIAG_EMIT` remains for legacy string-only paths; the five Story I hook sites use typed emits (see [Story I](./STORY_I_ngspice_diag_hooks.md)).

### AC-2: Hook points call typed emits

`niiter.c`, `devsup.c`, `cktop.c`, `dioload.c`, `spfactor.c` call **`ngspice_diag_emit_*`** (Story I locations).

### AC-3: PUB path is server-side

Workers attach the sink; `ngspice_server.c` packs **`DiagEvent`** and sends on **`sock_pub`** as multipart: **topic** (request id bytes) + **protobuf body**. Bind URLs: Story J2.

### AC-4: File and sink coexist

`diaghooks.c` may emit JSONL and invoke sink callbacks in the same emit when both file and sink are active.

### AC-5: Near-zero overhead when disabled

When `ngspice_diag_fp == NULL` and no relevant sink callbacks are registered, **`ngspice_diag_wants_*`** is false and hook sites skip work.

## Python client (cross-reference)

- **[`ngspice_client.py`](../../Studio-Portable-RAG/Codebase/ngspice/zmq_server/python/ngspice_client.py):** **`NgspiceClient`** — ZMQ **REQ** to REP; wire byte **`WIRE_SIM` (1)** + packed **`SimRequest`** / **`SimResult`**; constants **`WIRE_STATS` (3)** for stats-style probes that share the same framing convention.
- **`simulate_transient_async`** — async path uses **`AsyncZmqSimPool`** in **`ngspice_zmq_pool.py`** (**DEALER** → server ROUTER), not REQ.
- **`NgspiceDiagStream`** — ZMQ **SUB** on PUB; two-frame multipart (topic = `request_id`, body = **`DiagEvent`**). Defaults/env: **`NGSPICE_ZMQ_PUB_URL`**, **`NGSPICE_ZMQ_PUB_PORT`**; REP often **`NGSPICE_ZMQ_REP`** (see module and class docstrings).

Architecture: [Story I](./STORY_I_ngspice_diag_hooks.md) (hooks + JSONL) vs this document (server + PUB).

## Test Plan

```
Test ID | Description
--------|------------
J4-01   | Server mode: Python SUB client receives NRIteration events during simulation
J4-02   | Server mode: LimiterActivation events received when diode circuit runs
J4-03   | Server mode: DeviceLoad events contain correct vd, id, gd values
J4-04   | File mode still works (NGSPICE_DIAG_FILE produces valid JSONL)
J4-05   | Both modes active: file AND socket receive same events
J4-06   | Neither mode: no allocation, no crash, simulation runs normally
J4-07   | ZMQ_DONTWAIT prevents blocking if no subscriber is connected
J4-08   | 1000 events per second sustained without buffer overflow
```

## Definition of Done

- [x] Typed **`ngspice_diag_emit_*`** helpers implemented in `diaghooks.c`
- [x] Hook points call typed emits (not ad-hoc `DIAG_EMIT` for those hooks)
- [x] PUB socket publishes protobuf **`DiagEvent`** messages when server + `stream_diagnostics` are active
- [x] File mode (Story I) still works — `NGSPICE_DIAG_FILE`; manual recipe: [STORY_I Build & Test](./STORY_I_ngspice_diag_hooks.md#build--test)
- [x] File and sink modes can coexist (`diaghooks.c` dual path)
- [x] Near-zero overhead when diagnostics disabled (`ngspice_diag_wants_*` guards)

---

# STORY J5: Python Client Library

**Estimated effort:** 2–3 hours
**Files to create:** `python/ngspice_client.py`, `python/test_ngspice_client.py`
**Dependencies:** Story J1 (protobuf), Story J3 (server with simulation), Story J4 (diagnostic stream)

## Business Context

A Python client that NodalAI, the RAG MCP server, or any Python tool can use to run ngspice simulations over the socket and consume diagnostic streams — without subprocess spawning, file parsing, or shared library ctypes.

## Acceptance Criteria

### AC-1: Synchronous simulation API

```python
from ngspice_client import NgspiceClient

client = NgspiceClient("tcp://localhost:5555")

result = client.simulate("""
V1 in 0 5
R1 in out 1k
D1 out 0 D1N4148
.model D1N4148 D(IS=2.52e-9 N=1.752)
.op
.end
""")

print(result.converged)          # True
print(result.iterations)         # 12
print(result.node_voltages)      # {"in": 5.0, "out": 0.6523}
print(result.branch_currents)    # {"v1": -0.004347}
print(result.wall_time_ms)       # 2.3
```

### AC-2: Diagnostic stream consumer

```python
from ngspice_client import NgspiceDiagStream

stream = NgspiceDiagStream("tcp://localhost:5556")

# Collect all events for a specific request
events = stream.collect(request_id="req-001", timeout_sec=5.0)

nr_iters = [e.nr_iter for e in events if e.HasField("nr_iter")]
limiters = [e.limiter for e in events if e.HasField("limiter")]
devices = [e.device for e in events if e.HasField("device")]

print(f"NR iterations: {len(nr_iters)}")
print(f"Limiter activations: {len(limiters)}")
print(f"Device evaluations: {len(devices)}")
```

### AC-3: Comparison helper for NodalAI

```python
from ngspice_client import NgspiceClient

client = NgspiceClient()

def compare_dc_op(netlist: str, nodalai_voltages: dict) -> dict:
    """Run ngspice and diff against NodalAI results."""
    result = client.simulate(netlist)
    diff = {}
    for node, v_nodalai in nodalai_voltages.items():
        v_ngspice = result.node_voltages.get(node)
        if v_ngspice is not None:
            diff[node] = {
                "ngspice": v_ngspice,
                "nodalai": v_nodalai,
                "delta": abs(v_ngspice - v_nodalai),
                "match": abs(v_ngspice - v_nodalai) < 1e-6,
            }
    return diff
```

### AC-4: Context manager for connection lifecycle

```python
with NgspiceClient("tcp://localhost:5555") as client:
    result = client.simulate(netlist)
# Socket closed automatically
```

### AC-5: Timeout and error handling

```python
try:
    result = client.simulate(netlist, timeout_sec=10.0)
except NgspiceTimeoutError:
    print("Simulation timed out")
except NgspiceServerError as e:
    print(f"Server error: {e.error_code} — {e.message}")
```

## Test Plan

```
Test ID | Description
--------|------------
J5-01   | client.simulate() returns correct node voltages for resistor divider
J5-02   | client.simulate() returns correct diode Vd ≈ 0.65V
J5-03   | DiagStream.collect() receives NR iteration events
J5-04   | DiagStream.collect() receives limiter events for diode circuit
J5-05   | compare_dc_op() returns diff with match=True for correct NodalAI values
J5-06   | Timeout raises NgspiceTimeoutError after specified seconds
J5-07   | Invalid netlist returns error_code=PARSE_ERROR
J5-08   | Context manager closes socket on exit
J5-09   | 100 sequential simulations without resource leak
J5-10   | Stream filter by request_id only returns matching events
```

## Definition of Done

- [ ] `NgspiceClient` class with `simulate()` method
- [x] `NgspiceDiagStream` class with `collect()` method — **IMPLEMENTED** in `zmq_server/python/ngspice_client.py` (ZMQ SUB, topic-filtered `collect(request_id, timeout_sec)`)
- [ ] `compare_dc_op()` helper function
- [ ] Context manager support
- [ ] Timeout and error handling
- [ ] All 10 tests pass

---

# STORY J6: Performance Optimization — Circuit Pool and Batch Mode

**Estimated effort:** 2–3 hours
**Files to modify:** `src/server/ngspice_server.c`, `python/ngspice_client.py`
**Dependencies:** Story J3 (working simulation), Story J5 (Python client)

## Business Context

For the 76-circuit NodalAI benchmark, we need to run 76 simulations efficiently. This story adds circuit pooling (reuse CKT structs for repeated simulations of the same topology with different parameters) and batch request support.

## Acceptance Criteria

### AC-1: Batch simulation request

```protobuf
// Add to ngspice_sim.proto
message BatchSimRequest {
  repeated SimRequest requests = 1;
}

message BatchSimResult {
  repeated SimResult results = 1;
  double total_wall_time_ms = 2;
}
```

### AC-2: Python batch API

```python
results = client.simulate_batch([
    {"netlist": circuit1, "analysis": "op"},
    {"netlist": circuit2, "analysis": "op"},
    {"netlist": circuit3, "analysis": "op"},
])

# Returns list of SimResult in same order
for r in results:
    print(f"{r.request_id}: converged={r.converged}, time={r.wall_time_ms}ms")
```

### AC-3: Server-side memory pool

Instead of `malloc`/`free` per CKT struct, use a simple pool:

```c
#define POOL_SIZE 4
CKTcircuit *ckt_pool[POOL_SIZE];
int pool_next = 0;

CKTcircuit *pool_get() {
    CKTcircuit *ckt = ckt_pool[pool_next];
    if (ckt) CKTreset(ckt);  // clear state, keep allocated memory
    else ckt = CKTnew();     // first use: allocate
    return ckt;
}

void pool_return(CKTcircuit *ckt) {
    ckt_pool[pool_next] = ckt;
    pool_next = (pool_next + 1) % POOL_SIZE;
}
```

### AC-4: Performance target

76-circuit DC benchmark completes in under 10 seconds total (vs current ~60+ seconds with 76 separate `ngspice -b` invocations).

### AC-5: Benchmark script

```python
# python/benchmark_76.py
import time
from ngspice_client import NgspiceClient

client = NgspiceClient()
circuits = load_benchmark_manifest("tests/fixtures/internal_dc_benchmark_manifest.json")

start = time.time()
results = client.simulate_batch([{"netlist": c, "analysis": "op"} for c in circuits])
elapsed = time.time() - start

passed = sum(1 for r in results if r.converged)
print(f"76 circuits: {passed}/76 converged, {elapsed:.1f}s total, {elapsed/76*1000:.0f}ms avg")
```

## Test Plan

```
Test ID | Description
--------|------------
J6-01   | Batch of 10 circuits returns 10 results in correct order
J6-02   | Pool reuse: RSS memory stable across 100 sequential requests
J6-03   | Batch of 76 benchmark circuits completes in <10 seconds
J6-04   | Failed circuit in batch doesn't abort remaining circuits
J6-05   | Batch wall_time_ms is less than sum of individual wall_time_ms
J6-06   | Python benchmark script runs end-to-end
```

## Definition of Done

- [ ] BatchSimRequest/BatchSimResult protobuf messages
- [ ] Server handles batch requests
- [ ] CKT memory pool avoids re-allocation
- [ ] Python `simulate_batch()` API
- [ ] 76-circuit benchmark under 10 seconds
- [ ] Benchmark script works end-to-end

---

# STORY J7: Multi-analysis support (`.tran`, `.ac`, `.dc`)

**Estimated effort:** 3–4 hours  
**Files:** `zmq_server/proto/ngspice_sim.proto`, `zmq_server/ngspice_server.c`, `zmq_server/python/ngspice_client.py`, `zmq_server/tests/test_ngspice_sim_sweep.py`, fixtures under `zmq_server/tests/fixtures/circuits/`

## Summary

Extends Story J3 beyond DC OP: `SimRequest.analysis` may be `tran`, `ac`, or `dc`. The netlist must already contain the matching `.tran` / `.ac` / `.dc` line. The server runs `ngSpice_Command("run")` and collects multi-point results via sharedspice `SendInitData` / `SendData` into `SimResult.vectors` (`VectorData`: `name`, `real_values`, optional `imag_values` for AC). `SimResult.analysis_type` and `SimResult.num_points` describe the run. DC OP remains `ngSpice_Command("op")` with scalar `node_voltages` / `branch_currents` as before.

## Regenerating protobuf (C + Python)

From `Studio-Portable-RAG/Codebase/ngspice/zmq_server/`:

```bash
make -C proto regen    # Docker `znly/protoc` + host `protoc` for Python; fixes `#include` in .pb-c.c
```

Or install `protobuf-c-compiler` and run `protoc-c --c_out=. proto/ngspice_sim.proto`, copy `proto/ngspice_sim.pb-c.{c,h}` to `zmq_server/`, then replace `#include "proto/ngspice_sim.pb-c.h"` with `#include "ngspice_sim.pb-c.h"` in the `.c` file.

## Tests

Integration: `RUN_NGSPICE_SERVER=1 pytest zmq_server/tests/test_ngspice_sim_sweep.py`

---

# STORY J8: `ng.sh` service launcher

**Files:** `zmq_server/ng.sh`, `zmq_server/ng.yaml`, `zmq_server/ngspice_server.c` (`NG_SERVER_VERSION`, `--version`)

## Summary

Single entrypoint for ZMQ server + FastAPI bridge + Vite: **`./ng.sh help`** lists **`up`**, **`down`**, **`restart`**, **`status`**, **`probe`**, **`install`**, **`uninstall`** / **`remove`**. **`up`** prints the resolved YAML path, a full YAML dump of effective config, `SPICE_LIB_DIR`, libngspice version (via `strings`), **`ngspice-server --version`**, **`ldd`**-resolved shared libraries, Python **libzmq** / **pyzmq** / **uvicorn** versions, then brings each tier up with port checks. **`down`** stops **vite → bridge → zmq** with **SIGTERM** (process group for listeners), **SIGKILL** fallback, and port-release wait (Vite uses **`ss`** to store the real **node** PID because `npx` exits early). **`status`** shows PID / port / uptime from **`.ng/last_up.json`**. **`probe`** runs a tiny `.op` via **`ngspice_client`**. **`install`** writes a **systemd** unit (`Type=forking`, **PIDFile** = `.ng/zmq_server.pid`); use **`--system`** for `/etc/systemd/system/` (root). Keep **`service.version`** in **`ng.yaml`** aligned with **`NG_SERVER_VERSION`** in C.

---

## Story Dependency Graph

```
J1 (proto schema)
 └─→ J2 (ZMQ server shell)
      └─→ J3 (wire to ngspice core)
           ├─→ J4 (route hooks to PUB socket)  ← requires Story I hooks
           └─→ J5 (Python client library)
                └─→ J6 (batch + pool optimization)
                     └─→ J7 (tran / ac / dc sweeps + VectorData on SimResult)
                          └─→ J8 (ng.sh / ng.yaml stack launcher + systemd install)
```

Implement in order: J1 → J2 → J3 → J4 → J5 → J6 → J7 (J7 builds on J3/J5/J6). J8 is optional ops polish on top of J7.

Stories J1 and J2 can be done without Story I. Story J4 requires Story I's hook points to be in place.

---

## System Dependencies

```bash
# Ubuntu/Debian
sudo apt install libzmq3-dev protobuf-c-compiler libprotobuf-c-dev

# Python
pip install pyzmq protobuf

# Verify
python3 -c "import zmq; print(f'ZMQ {zmq.zmq_version()}')"
protoc --version
protoc-c --version
```
