# VVADomainRAG + NodalAI — Master Story Tracker

> **Last updated:** 2026-04-21
> **Repos:** `mandnArgiTech/VVADomianRAG` (branch `ngspice_rag`), `mandnArgiTech/NodalAI` (branch `main`)
> **Mission:** Make ngspice AI-ready. Use ngspice's 40-year validated physics as a reference oracle to fix NodalAI's Python MNA solver via structured diagnostic comparison.

---

## RAG Pipeline Stories (VVADomianRAG repo) — ALL DONE

| Story | Title | Status | Key Output |
|-------|-------|--------|------------|
| **A** | Structural Importance Scoring | ✅ Done | `structural_importance` float on every code chunk |
| **B** | Call-Graph Metadata | ✅ Done | `calls` field → callee expansion in MCP |
| **C** | Domain Doc Ingestion | ✅ Done | 176 ngspice chapters, concept registry |
| **D** | Gemma 3 QAT Default | ✅ Done | `gemma3:27b-it-qat`, system prompts per domain |
| **E** | Cross-Encoder Reranker | ✅ Done | `bge-reranker-v2-m3`, opt-in `RAG_RERANKER=1` |
| **F** | Chunk Min-Size Merging | ✅ Done | Section-boundary merge, calls/concepts union |
| **G** | Multi-Domain (5 domains) | ✅ Done | spice/kinematica/mujoco/nav2/dart |
| **H** | Ingest Quality Filters | ✅ Done | Declaration <200 chars dropped, God mode denylist |

## ngspice AI-Ready Stories (VVADomianRAG repo) — ALL DONE

| Story | Title | Status | Key Output |
|-------|-------|--------|------------|
| **I** | Diagnostic Hooks (5 C hooks) | ✅ Done | `nr_iter`, `limiter`, `gmin`, `device`, `matrix` hooks |
| **J1** | Protobuf Schema | ✅ Done | `SimRequest`, `SimResult`, `DiagEvent` proto messages |
| **J2** | ZMQ Server Shell | ✅ Done | REP :5555 + PUB :5556, signal handling |
| **J3** | Wire to ngspice Core | ✅ Done | Netlist → CKT → simulate → voltages via sharedspice |
| **J4** | Route Hooks to PUB Socket | ✅ Done | Story I hooks stream as protobuf DiagEvents |
| **J5** | Python Client Library | ✅ Done | `NgspiceClient`, `NgspiceDiagStream` |
| **J6** | Batch + CKT Pool | ✅ Done | 76-circuit batch, memory pool |
| **J7** | Multi-Analysis | ✅ Done | `.tran`/`.ac`/`.dc` + `VectorData` waveforms |
| **J8** | `ng.sh` Launcher | ✅ Done | up/down/status/probe/install, systemd, `ng.yaml` |

## NodalAI Integration Stories (NodalAI repo) — IN PROGRESS

| Story | Title | Status | Effort | Key Output |
|-------|-------|--------|--------|------------|
| **L1** | NgspiceZMQAdapter | ⬜ Not started | 3–4 hrs | 4th solver path in `ecad/solver.py` |
| **L2** | ConvergenceDiff | ⬜ Not started | 3–4 hrs | Root cause + `suggested_fixes` with file:line |
| **L3** | `/api/convergence-debug` | ⬜ Not started | 2–3 hrs | Always-on comparison endpoint |
| **L4** | MCP tool + benchmark | ⬜ Not started | 4–5 hrs | Cursor reads diff → writes fix → circuits pass |

## Frontend Stories (NodalAI repo) — NOT STARTED

| Story | Title | Status | Effort | Depends On |
|-------|-------|--------|--------|------------|
| **K1** | Fix CodeMirror Editing Bugs | ⬜ | 2–3 hrs | — |
| **K2** | Lezer SPICE Grammar | ⬜ | 4–5 hrs | — |
| **K3** | IntelliJ Dockable Layout | ⬜ | 6–8 hrs | — |
| **K4** | Complete Menu Bar | ⬜ | 3–4 hrs | K1, K3 |
| **K5** | YAML Configuration System | ⬜ | 3–4 hrs | K3 |
| **K6** | About Dialog | ⬜ | 2–3 hrs | K4 |
| **K7** | Modular Kernel Adapter | ⬜ | 5–6 hrs | K5, L1 |
| **K8** | Docker + On-Prem Deploy | ⬜ | 4–5 hrs | K7 |

---

## Domain Docs / Ingest Status

| Domain | Code Ingested | Domain Docs | Ready to Ingest? |
|--------|--------------|-------------|-----------------|
| **spice** | ✅ ngspice src | ✅ 178 chapters + io_dataflow + pageindex | Done |
| **kinematica** | ⬜ ardupilot | ✅ 112 chapters + nav2_pageindex | Yes — run ingest |
| **mujoco** | ⬜ | ⬜ | No docs yet |
| **nav2** | ⬜ | ✅ nav2_pageindex | Partial |
| **dart** | ⬜ | ⬜ | No docs yet |

**Ingest kinematica now:**
```bash
export EMBEDDING_MODEL=mxbai-embed-large
./run.sh --mode code --domain kinematica --source ./Studio-Portable-RAG/Codebase/ardupilot --force
./run.sh --mode domain --domain kinematica --source ./Studio-Portable-RAG/DomainDocs/kinematica --force
```

---

## Real Bug Found via Code Audit (Story L will fix)

**File:** `ecad/mna/newton_raphson.py:1044` (and `:1066`, `transient.py:1481, 1498`)

```python
# CURRENT — WRONG for non-default IS diodes:
vcrit_lim = 0.7   # hardcoded fallback

# CORRECT — IS-dependent, already computed on DiodeModel:
dmod = device_cache.get(c["id"])
vcrit_lim = float(getattr(dmod, "vcrit", 0.7))
# DiodeModel.vcrit = N_VT * log(N_VT / (sqrt(2) * IS))  [ecad/devices/diode.py:59]
```

**Impact:** D1N4148 (IS=2.52e-9): correct vcrit≈0.61V, fallback 0.7V → 14% wider NR steps → slower/failed convergence. Story L4 benchmark will identify exactly which of the 76 benchmark circuits fail because of this.

---

## Execution Priority

```
Phase 1: RAG quality (A–H)          ✅ DONE
Phase 2: ngspice AI-ready (I–J8)    ✅ DONE — circuits working with speed
Phase 3: Integration (L1–L4)        ← NEXT — wire ZMQ to NodalAI, fix bugs
Phase 4: Frontend IDE (K1–K8)       ← After L series
Phase 5: Ingest kinematica          ← Can run in parallel with L
```

## Dependency Graph

```
VVADomianRAG:                       NodalAI:
A–H (RAG) ✅                        MNA solver (ecad/mna/)
I (hooks) ✅ ─────────────────────→  L1: NgspiceZMQAdapter
J1–J8 (ZMQ) ✅ ──────────────────→  L2: ConvergenceDiff
                                     L3: /api/convergence-debug
I + J + L ──→ RAG MCP tool ──────→  L4: get_convergence_diff
                                          │
                                          ▼
                                     Cursor reads diagnosis
                                     fixes newton_raphson.py:1044
                                     circuits pass benchmark
```
