# ngspice vs NodalAI — What the Controversy Gets Right and Wrong

> This document addresses six specific claims made against ngspice in the context of
> the VVADomainRAG + NodalAI architecture. Each claim is evaluated against what we
> actually built (Stories I, J1–J8, L1–L4) vs what the critic assumes.

---

## The Critic's Core Assumption (Wrong)

The controversy assumes ngspice is being used as a **replacement** for NodalAI. It is not.

In our architecture, ngspice is used as a **reference oracle** and **convergence debugger**:

- NodalAI is the primary simulator (REST API, browser-native, JAX-differentiable, Python-extensible)
- ngspice is the ground truth that tells us *what the correct answer is* and *how it got there*
- Story L wires them together so ngspice's numerical trace becomes NodalAI's fix guide

With that framing, let's go through each claim:

---

## Claim 1: "ngspice can't run in a browser"

> "It's a compiled C binary. You can't embed it in a web app, a mobile app, or a cloud IDE. Every user needs to install it locally. NodalAI runs in any browser — zero install."

**What the critic gets right:**
ngspice cannot run inside a browser tab. There is no WASM build of ngspice that handles the full simulation stack (sharedspice + sparse matrix + all device models). Correct.

**What the critic misses:**

Our architecture (Story J, J8) runs ngspice as a **persistent ZMQ server** on the same machine as NodalAI's backend — not in the browser. The browser never touches ngspice directly:

```
Browser (React)
    │  HTTP /api/simulate
    ▼
NodalAI FastAPI (Python)
    │  ZMQ tcp://localhost:5555
    ▼
ngspice ZMQ server (C process)
    │
    └─ PUB :5556 (diagnostic stream)
```

The user has **zero interaction with ngspice**. They click "Simulate" in the browser. NodalAI's backend decides whether to use internal MNA, the ZMQ server, or both. The ZMQ server is a backend infrastructure concern, like a database — users don't install PostgreSQL in their browser either.

**Story J8 (`ng.sh`)** handles install with one command:
```bash
./ng.sh install --system   # writes systemd unit, auto-starts on boot
```

**In Docker mode (Story K8):**
```yaml
services:
  frontend: nginx + React
  backend: FastAPI (NodalAI)
  ngspice: ZMQ server       ← containerized, user never sees it
```

**Verdict:** The claim is valid for ngspice-as-IDE. It does not apply to ngspice-as-backend-service.

---

## Claim 2: "ngspice has no API"

> "To simulate a circuit, you write a text file, run a command, parse the output file. There's no POST /simulate endpoint. NodalAI has a REST API."

**What the critic gets right:**
The stock ngspice binary is CLI-only. No REST, no socket, no structured output. Correct.

**What the critic misses:**

This is precisely what Stories J1–J8 fixed. The ngspice ZMQ server **is** a structured API:

```protobuf
// ngspice_sim.proto (Story J1)
message SimRequest {
  string netlist = 1;
  string analysis = 2;        // "op" | "tran" | "ac" | "dc"
  map<string, double> options = 3;
  bool stream_diagnostics = 4;
  string request_id = 5;
}

message SimResult {
  bool converged = 1;
  int32 iterations = 2;
  map<string, double> node_voltages = 3;
  map<string, double> branch_currents = 4;
  repeated VectorData vectors = 5;    // tran/ac waveforms
  double wall_time_ms = 6;
  ErrorCode error = 7;
}
```

Story J5 provides a Python client:
```python
from ngspice_client import NgspiceClient
client = NgspiceClient("tcp://localhost:5555")
result = client.simulate(netlist, analysis="op")
print(result.node_voltages)   # {"v(out)": 0.651, ...}
```

Story J7 adds `.tran`, `.ac`, `.dc` with waveform vectors. Story J6 adds batch mode for 76 circuits at once.

**Verdict:** The claim describes stock ngspice. It does not apply to the Story J ZMQ server. We built the API layer the critic says doesn't exist.

---

## Claim 3: "ngspice can't be differentiated"

> "You can't compute dV(out)/dR1. NodalAI has JAX integration (D5EX-12) — the entire MNA solver is differentiable."

**What the critic gets right:**
ngspice cannot compute analytic gradients. Confirmed — no JAX, no autograd, no sensitivity via AD. Correct.

**What the critic misses:**

We are not using ngspice for gradient computation. NodalAI does that. ngspice's role is **reference verification** — confirming that the DC operating point or transient result is correct before trusting a gradient.

The workflow is:
1. JAX-differentiated NodalAI computes `dV(out)/dR1` by gradient descent
2. For each candidate solution, NodalAI optionally verifies against ngspice ZMQ (Story L)
3. If ngspice disagrees → NodalAI's forward pass has a bug → fix the bug before trusting the gradient

ngspice also supports **numerical sensitivity** via `.sens` analysis and DC sweep, which can approximate `dV/dR` to first order. Not autograd, but useful for sanity checks.

**Verdict:** Fully correct — ngspice cannot differentiate. This is not a use case we assign to it.

---

## Claim 4: "ngspice can't explain itself"

> "When a simulation fails, you get cryptic messages like 'singular matrix'. There's no structured error object, no convergence hints, no machine-readable diagnostics. NodalAI returns JSON with convergence_hints."

**What the critic gets right:**
Stock ngspice's error output is human-readable stderr text, not structured JSON. Parsing it requires regex. Correct.

**What the critic misses:**

This is exactly what **Story I** fixed. We added 5 structured diagnostic hooks directly into ngspice's C source:

| Hook | Location | What it emits |
|------|----------|---------------|
| `nr_iter` | `niiter.c` | `{iter, max_dx, noncon, converged}` per NR step |
| `limiter` | `devsup.c` | `{fn, vnew_raw, vnew_lim, vold, vcrit}` when DEVpnjlim fires |
| `gmin` | `cktop.c` | `{value, converged, iters}` per GMIN stepping level |
| `device` | `dioload.c` | `{type, inst, vd, id, gd, ieq}` per device per iteration |
| `matrix` | `spfactor.c` | `{size, min_piv, max_piv, ratio}` after LU factorization |

These emit to the ZMQ PUB socket as **protobuf DiagEvent messages** (Story J4), not stderr text.

Story L2 (`compute_convergence_diff`) reads these events and produces structured diagnosis:

```json
{
  "diagnosis": [
    "NodalAI needed 200 NR iterations; ngspice converged in 12.",
    "ngspice's DEVpnjlim fired 3 times. Max clamp: 1.820V → 0.683V.",
    "NodalAI vcrit may be too high or limiter is not being called."
  ],
  "suggested_fixes": [
    "Check _limit_junction_voltage() in mna_solver.py: vcrit = vt * log(vt / (sqrt(2)*IS))"
  ]
}
```

**Verdict:** The claim describes stock ngspice stderr. Story I + J4 + L2 replace that with structured protobuf diagnostics and automated AI-readable diagnosis. This is the biggest gap we specifically closed.

---

## Claim 5: "ngspice can't be AI-prompted"

> "There's no way to say 'add a Schottky diode between nodes 3 and 4 using a real part.' NodalAI has a 15,000-part library and AI prompt builder."

**What the critic gets right:**
ngspice has no concept of a part library, reference designators, or natural-language component insertion. You write raw SPICE text. Correct.

**What the critic misses:**

ngspice does not need to be AI-prompted because **NodalAI handles the front-end intelligence**. The AI flow is:

1. AI agent (Cursor) uses NodalAI's part library + prompt builder to assemble a circuit
2. NodalAI generates a SPICE netlist
3. That netlist goes to ngspice ZMQ server as a string
4. ngspice simulates it, returns structured results

ngspice's input is always a netlist string. It never needs to "understand" what a Schottky diode is by name — that translation is NodalAI's job.

For VVADomainRAG, the RAG serves SPICE knowledge so Cursor can write correct SPICE. ngspice validates that the SPICE is physically correct. These are complementary, not competing roles.

**Verdict:** Correct that ngspice itself cannot be AI-prompted. This is not a capability we need from ngspice.

---

## Claim 6: "ngspice is monolithic C — impossible for AI to modify"

> "If an AI agent needs to add a new device model, it would need to modify C code, recompile, and redeploy. In NodalAI, device models are Python dataclasses — an AI can write a new @dataclass class MyDevice and it works immediately."

**What the critic gets right:**
Adding a device model to ngspice requires writing C, regenerating the vtable, modifying `DEVices[]`, recompiling, and redeploying. An AI agent cannot do this safely in a running production system. Correct.

**What the critic misses:**

We are not asking the AI to add device models to ngspice. We are asking it to add device models to **NodalAI** (Python dataclasses, hot-reloadable). ngspice's existing device models (70+ in the source tree) serve as the **reference implementations** — not as the deployment target.

The workflow for a new device model (e.g., GaN HEMT):
1. AI agent reads the ngspice GaN HEMT C source via VVADomainRAG RAG
2. AI agent writes a Python `@dataclass class GaNHEMT` in NodalAI
3. AI agent verifies the new Python model against ngspice's C model using Story L's convergence diff
4. When the Python model matches ngspice within tolerance, it ships

ngspice's C code is the **spec and test oracle**, not the development target. VVADomainRAG's Story C ingested 176 ngspice device chapters precisely so this reading step is fast and accurate.

**What is a real gap:**

The ngspice C codebase being monolithic means we cannot add new hooks or diagnostic instrumentation without recompile. If we need a new Story I hook (e.g., per-timestep LTE tracking for transient), that requires a C change and rebuild. This is a genuine friction point.

**Mitigation:** `ng.sh` (Story J8) makes this a one-command operation: `./ng.sh down && make -j$(nproc) && ./ng.sh up`. Managed as a submodule — Story I patch is tracked in git, not applied manually.

**Verdict:** Correct that C modifications require recompile. This is a real operational cost, partially mitigated by `ng.sh` and the patch workflow.

---

## The Real Answer: Role Separation

The controversy conflates two different uses of ngspice:

| Use Case | ngspice as IDE Tool | ngspice in our Architecture |
|---|---|---|
| User interaction | Installs locally, runs CLI | Never touches ngspice |
| API | None (CLI only) | REST-equivalent via ZMQ protobuf (Story J) |
| Error reporting | Cryptic stderr | Structured DiagEvent stream (Story I + J4) |
| AI integration | Impossible | Via MCP tool, reads ConvergenceDiff (Story L4) |
| Differentiability | None | Not required of ngspice (NodalAI handles this) |
| Device models | C only, recompile | Read as oracle; Python impl in NodalAI |
| Browser | Cannot run | Runs as backend service, not in browser |

**The correct framing:**

ngspice is a **40-year-old battle-tested reference implementation** of SPICE physics. NodalAI is a **modern Python reimplementation** of the same physics with better APIs, differentiability, and AI integration.

We use ngspice to catch the bugs in NodalAI's physics. When NodalAI's diode limiter gets the vcrit formula wrong (vcrit=0.7 hardcoded vs vcrit=vt*log(vt/√2·IS) dynamic), ngspice's diagnostic stream shows the exact voltage where NodalAI diverges. That is its only job. It does that job extremely well.

---

## What This Architecture Actually Delivers

| Claim | Stock ngspice | ngspice in our Architecture |
|---|---|---|
| Browser access | ❌ | ✅ Backend service, transparent to browser |
| Structured API | ❌ | ✅ ZMQ protobuf (Story J1–J5) |
| Structured diagnostics | ❌ | ✅ 5 hooks, DiagEvent stream (Story I + J4) |
| AI-readable errors | ❌ | ✅ ConvergenceDiff + diagnosis (Story L2) |
| Differentiability | ❌ | N/A — NodalAI handles this |
| AI-prompted | ❌ | N/A — NodalAI handles this |
| Python-extensible | ❌ | N/A — NodalAI handles this |
| New hooks without recompile | ❌ | ❌ (genuine limitation, mitigated by ng.sh) |
| WASM / edge deployment | ❌ | ❌ (genuine limitation) |

---

## Two Genuine Gaps to Acknowledge

**Gap 1: No WASM / edge deployment.**
If the use case requires running simulation in a serverless edge function, a mobile app, or a browser with no backend, ngspice cannot participate. NodalAI's Python kernel could theoretically run in Pyodide (WASM Python), but ngspice cannot. For our current use case (workstation + server), this is not a constraint.

**Gap 2: New diagnostic hooks require recompile.**
Story I's 5 hooks cover the NR loop, limiter, GMIN, device load, and matrix. If a future analysis needs a new hook (e.g., time-step LTE tracking, source stepping detail), that requires a C change + rebuild + submodule bump. With `ng.sh` this is fast, but it is not hot-pluggable the way a Python decorator would be. This is a genuine architectural cost of using C as the hook surface.

**Both gaps are acceptable** for the current use case: a local/on-prem circuit simulation IDE with an AI debugging loop. Neither gap affects the primary value proposition — using ngspice's physics as the reference oracle to fix NodalAI's convergence bugs.
