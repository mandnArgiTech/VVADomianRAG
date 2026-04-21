# VVADomainRAG + NodalAI — Master Story Tracker

> **Last updated:** 2026-04-21
> **Repos:** `mandnArgiTech/VVADomianRAG` (branch `ngspice_rag`), `mandnArgiTech/NodalAI` (branch `main`)

---

## RAG Pipeline Stories (VVADomianRAG repo)

| Story | Title | Status | Tests | Notes |
|-------|-------|--------|-------|-------|
| **A** | Structural Importance Scoring | ✅ Done | 13 pass | `#include` ref counting → `structural_importance` metadata |
| **B** | Call-Graph Metadata | ✅ Done | 17 pass | `calls` metadata via tree-sitter, MCP callee expansion |
| **C** | Domain Doc Ingestion | ✅ Done | 17 pass | 176 ngspice chapters, `source_c_files`, concept registry 62 entries |
| **D** | Gemma 3 QAT Default | ✅ Done | 12 pass | `gemma3:27b-it-qat`, fallback chain, system prompts |
| **E** | Cross-Encoder Reranker | ✅ Done | 15 pass | `bge-reranker-v2-m3`, opt-in `RAG_RERANKER=1`, both return paths |
| **F** | Chunk Min-Size Merging | ✅ Done | 15 pass | `_merge_small_chunks`, section-boundary aware, calls/concepts union |
| **G** | Multi-Domain (5 Domains) | ✅ Done | 20 pass | spice/kinematica/mujoco/nav2/dart, prefix domain filter, 5 system prompts |
| **H** | Ingest Quality Filters | ✅ Done | 12 pass | Code chunk min size, declaration filter <200, God mode denylist, expanded gitignore |

## ngspice Instrumentation Stories (VVADomianRAG repo, applied to ngspice submodule)

| Story | Title | Status | Notes |
|-------|-------|--------|-------|
| **I** | ngspice C Diagnostic Hooks | ✅ Done | 5 hooks (NR iter, limiter, GMIN, device, matrix), committed to submodule |
| **J1** | Protobuf Schema | ✅ Done | `ngspice_sim.proto` with SimRequest/SimResult/DiagEvent |
| **J2** | ZMQ Server Shell | ✅ Done | REP :5555, PUB :5556, signal handling |
| **J3** | Wire to ngspice Core | ✅ Done | Netlist → CKT → simulate → voltages via sharedspice |
| **J4** | Route Hooks to PUB Socket | ✅ Done | Protobuf DiagEvent stream, file+socket coexist |
| **J5** | Python Client Library | ✅ Done | `NgspiceClient`, `NgspiceDiagStream` |
| **J6** | Batch + Pool Optimization | ✅ Done | BatchSimRequest, CKT pool |
| **J7** | Multi-Analysis (.tran/.ac/.dc) | ✅ Done | VectorData on SimResult, SendData callbacks |
| **J8** | `ng.sh` Service Launcher | ✅ Done | up/down/status/probe/install, systemd, ng.yaml config |

## Domain Docs Status

| Domain | Code Ingested | Domain Docs | Chapters | Concept Registry |
|--------|--------------|-------------|----------|-----------------|
| **spice** | ✅ ngspice src (with Story H filters) | ✅ 176 chapters + io_dataflow + pageindex | 178 | 62 entries |
| **kinematica** | ⬜ Not yet | ✅ 110 chapters + nav2_pageindex | 112 | 51 entries |
| **mujoco** | ⬜ Not yet | ⬜ Not yet | 0 | 35 entries |
| **nav2** | ⬜ Not yet | ✅ nav2_pageindex (1 doc) | 1 | 34 entries |
| **dart** | ⬜ Not yet | ⬜ Not yet | 0 | 28 entries |

## NodalAI Frontend Stories (NodalAI repo)

| Story | Title | Status | Effort | Depends On |
|-------|-------|--------|--------|------------|
| **K1** | Fix CodeMirror Editing Bugs | ⬜ Not started | 2–3 hrs | — |
| **K2** | Lezer SPICE Grammar | ⬜ Not started | 4–5 hrs | — |
| **K3** | IntelliJ Dockable Layout | ⬜ Not started | 6–8 hrs | — |
| **K4** | Complete Menu Bar (File/Edit/View/Help) | ⬜ Not started | 3–4 hrs | K1, K3 |
| **K5** | YAML Configuration System | ⬜ Not started | 3–4 hrs | K3 |
| **K6** | About Dialog (version, build, deps) | ⬜ Not started | 2–3 hrs | K4 |
| **K7** | Modular Kernel Adapter (pluggable backend) | ⬜ Not started | 5–6 hrs | K5, Story J |
| **K8** | Docker + On-Prem Deployment | ⬜ Not started | 4–5 hrs | K7 |

---

## Execution Priority

### Phase 1 — RAG Quality (DONE)
Stories A→H: all implemented. Retrieval quality validated with reranker + quality filters.

### Phase 2 — ngspice Instrumentation (DONE)
Stories I→J8: all implemented. ngspice is now a ZMQ simulation server with diagnostic hooks.

### Phase 3 — Ingest Remaining Domains (NEXT)
```bash
export EMBEDDING_MODEL=mxbai-embed-large

# Kinematica code + docs (110 chapters ready)
./run.sh --mode code --domain kinematica --source ./Studio-Portable-RAG/Codebase/ardupilot --force
./run.sh --mode domain --domain kinematica --source ./Studio-Portable-RAG/DomainDocs/kinematica --force

# Nav2 code
./run.sh --mode code --domain nav2 --source /path/to/navigation2 --force

# MuJoCo code
./run.sh --mode code --domain mujoco --source /path/to/mujoco/src --force

# DART code
./run.sh --mode code --domain dart --source /path/to/dart --force
```

### Phase 4 — Frontend IDE (NodalAI repo)
Stories K1→K8: transform vidhubijakam-demo into a professional, modular, Docker-ready IDE.

### Phase 5 — Integration
- Connect vidhubijakam-demo to ngspice ZMQ server (K7 + J)
- Connect VVADomainRAG MCP server to Cursor for NodalAI development
- Run 76-circuit benchmark through ZMQ server, compare with NodalAI

---

## Cross-Story Dependencies

```
VVADomianRAG repo:                    NodalAI repo:
A─H (RAG pipeline) ✅                 K1 (editor fixes)
    │                                  K2 (Lezer grammar)
    │                                  K3 (docking layout)
    │                                  K4 (menus) ← K1, K3
I (diag hooks) ✅                      K5 (YAML config) ← K3
    │                                  K6 (About) ← K4
J1─J8 (ZMQ server) ✅ ──────────────→ K7 (kernel adapter) ← K5, J
                                       K8 (Docker) ← K7
```
