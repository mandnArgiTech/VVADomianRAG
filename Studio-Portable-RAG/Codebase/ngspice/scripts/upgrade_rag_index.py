#!/usr/bin/env python3
"""
Upgrade rag_index.json per RAG Index Upgrade Plan:
  - book_docs from docs/ngspice_book/**/*.md
  - cross-link source related_files from _meta/source_file_attribution.json
  - imported_by backfill from c_includes_internal
  - numerical_constants_defined on cktdefs.h (field semantics + CKTinit defaults)
  - summaries for all indexed files (source-derived)
  - call_graph_outgoing for kernel files + DEVload/DEVacLoad device files
  - schema bump to 1.1
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))
from backfill_imported_by import backfill_imported_by_only
from build_rag_index import (
    CKTDEFS_H_NUMERICAL_METADATA,
    DEV_DIR_TO_KIND,
    circuit_designer_topic_for,
    device_family_from_path,
    expand_call_graph_for_all_records,
    numerical_constants_for_translation_unit,
    offdevice_spicedev_tags,
    resolve_spicedev_implemented,
    spice_analysis_role_for,
)

try:
    import yaml
except ImportError as e:  # pragma: no cover
    raise SystemExit("PyYAML is required: pip install pyyaml") from e

REPO_ROOT = Path(__file__).resolve().parent.parent
RAG_PATH = REPO_ROOT / "rag_index.json"
BOOK_ROOT = REPO_ROOT / "docs" / "ngspice_book"
ATTRIBUTION_PATH = BOOK_ROOT / "_meta" / "source_file_attribution.json"

BOILERPLATE_RE = re.compile(
    r"^ngspice source at .+: .+ component \(.+\)\. See path and symbols for retrieval\.$"
)

# Known helpers -> implementation file (repo-relative)
DEVSUP_FUNCS: frozenset[str] = frozenset(
    {
        "DEVpnjlim",
        "DEVfetlim",
        "DEVlimvds",
        "DEVcmeyer",
        "DEVqmeyer",
        "DEVcap",
        "DEVpred",
    }
)
DEVSUP_PATH = "src/spicelib/devices/devsup.c"

# Device files whose implementation often calls devsup / same-TU DEV* / kernel helpers
CALL_GRAPH_RELEVANT_SPICEDEV: frozenset[str] = frozenset(
    {
        "DEVload",
        "DEVacLoad",
        "DEVtrunc",
        "DEVnoise",
        "DEVconvTest",
        "DEVtemperature",
        "DEVparam",
        "DEVsetic",
        "DEVpzLoad",
        "DEVdisto",
        "DEVaccept",
        "DEVfindBranch",
        "DEVsoaCheck",
        "DEVsenLoad",
        "DEVsenUpdate",
        "DEVsenPrint",
        "DEVdump",
        "DEVdestroy",
        "DEVdelete",
        "DEVsetup",
        "DEVmParam",
        "DEVmodAsk",
        "DEVask",
    }
)

ANALYSIS_CALLEES: dict[str, tuple[str, str]] = {
    "NIintegrate": ("src/maths/ni/niinteg.c", "NIintegrate"),
    "CKTterr": ("src/spicelib/analysis/cktterr.c", "CKTterr"),
}

KERNEL_CALL_GRAPHS: dict[str, list[dict[str, Any]]] = {
    "src/maths/ni/niiter.c": [
        {"symbol": "NIiter", "target_file": "src/spicelib/analysis/cktload.c", "target_symbol": "CKTload", "indirect": False},
        {"symbol": "NIiter", "target_file": "src/maths/sparse/spsmp.c", "target_symbol": "SMPluFac", "indirect": False},
        {"symbol": "NIiter", "target_file": "src/maths/sparse/spsmp.c", "target_symbol": "SMPsolve", "indirect": False},
        {"symbol": "NIiter", "target_file": "src/maths/ni/niconv.c", "target_symbol": "NIconvTest", "indirect": False},
        {"symbol": "NIiter", "target_file": "src/spicelib/analysis/cktload.c", "target_symbol": "DEVices[]->DEVload", "indirect": True},
    ],
    "src/maths/ni/niaciter.c": [
        {"symbol": "NIacIter", "target_file": "src/spicelib/analysis/acan.c", "target_symbol": "CKTacLoad", "indirect": False},
        {"symbol": "NIacIter", "target_file": "src/maths/sparse/spsmp.c", "target_symbol": "SMPcLUfac", "indirect": False},
        {"symbol": "NIacIter", "target_file": "src/maths/sparse/spsmp.c", "target_symbol": "SMPcSolve", "indirect": False},
        {"symbol": "NIacIter", "target_file": "src/spicelib/analysis/acan.c", "target_symbol": "DEVices[]->DEVacLoad", "indirect": True},
    ],
    "src/spicelib/analysis/cktload.c": [
        {"symbol": "CKTload", "target_file": "src/spicelib/analysis/cktload.c", "target_symbol": "DEVices[]->DEVload", "indirect": True},
    ],
    "src/spicelib/analysis/cktop.c": [
        {"symbol": "CKTop", "target_file": "src/maths/ni/niiter.c", "target_symbol": "NIiter", "indirect": False},
        {"symbol": "CKTop", "target_file": "src/spicelib/analysis/cktop.c", "target_symbol": "dynamic_gmin", "indirect": False},
        {"symbol": "CKTop", "target_file": "src/spicelib/analysis/cktop.c", "target_symbol": "spice3_gmin", "indirect": False},
        {"symbol": "CKTop", "target_file": "src/spicelib/analysis/cktop.c", "target_symbol": "gillespie_src", "indirect": False},
        {"symbol": "CKTop", "target_file": "src/spicelib/analysis/cktop.c", "target_symbol": "spice3_src", "indirect": False},
    ],
    "src/spicelib/analysis/dcop.c": [
        {"symbol": "DCop", "target_file": "src/spicelib/analysis/cktop.c", "target_symbol": "CKTop", "indirect": False},
        {
            "symbol": "DCop",
            "target_file": "src/maths/ni/niiter.c",
            "target_symbol": "NIiter",
            "indirect": True,
            "note": "CKTop invokes NIiter for the inner Newton loop during DC OP.",
        },
        {"symbol": "DCop", "target_file": "src/spicelib/analysis/cktload.c", "target_symbol": "CKTload", "indirect": False},
    ],
    "src/spicelib/analysis/dctran.c": [
        {"symbol": "DCtran", "target_file": "src/maths/ni/niiter.c", "target_symbol": "NIiter", "indirect": False},
        {
            "symbol": "DCtran",
            "target_file": "src/maths/ni/niinteg.c",
            "target_symbol": "NIintegrate",
            "indirect": True,
            "note": "Transient capacitors reach NIintegrate from device DEVload paths each NR iteration.",
        },
        {"symbol": "DCtran", "target_file": "src/spicelib/analysis/ckttrunc.c", "target_symbol": "CKTtrunc", "indirect": False},
        {"symbol": "DCtran", "target_file": "src/spicelib/devices/cktaccept.c", "target_symbol": "CKTaccept", "indirect": False},
    ],
    "src/spicelib/analysis/acan.c": [
        {"symbol": "ACan", "target_file": "src/spicelib/analysis/cktop.c", "target_symbol": "CKTop", "indirect": False},
        {"symbol": "ACan", "target_file": "src/spicelib/analysis/cktload.c", "target_symbol": "CKTload", "indirect": False},
        {"symbol": "ACan", "target_file": "src/maths/ni/niaciter.c", "target_symbol": "NIacIter", "indirect": False},
        {"symbol": "CKTacLoad", "target_file": "src/spicelib/analysis/acan.c", "target_symbol": "DEVices[]->DEVacLoad", "indirect": True},
    ],
    "src/maths/ni/niconv.c": [
        {
            "symbol": "NIconvTest",
            "target_file": "src/maths/sparse/spsmp.c",
            "target_symbol": "SMPmatSize",
            "indirect": False,
        },
        {
            "symbol": "NIconvTest",
            "target_file": "src/spicelib/analysis/cktop.c",
            "target_symbol": "CKTconvTest",
            "indirect": False,
            "note": "Only when compiled with NEWCONV; otherwise node-only test.",
        },
    ],
    "src/maths/ni/niinteg.c": [
        {
            "symbol": "NIintegrate",
            "target_file": "src/maths/ni/nicomcof.c",
            "target_symbol": "NIcomCof",
            "indirect": True,
            "note": "Uses ckt->CKTag[] filled earlier by NIcomCof for this timestep.",
        },
    ],
    "src/maths/ni/nicomcof.c": [
        {
            "symbol": "NIcomCof",
            "target_file": "src/include/ngspice/cktdefs.h",
            "target_symbol": "CKTintegrateMethod / CKTorder / CKTdelta",
            "indirect": True,
            "note": "Reads timestep and method/order from CKTcircuit; writes CKTag/CKTagp.",
        },
    ],
    "src/maths/ni/nipred.c": [
        {
            "symbol": "NIpred",
            "target_file": "src/maths/sparse/spsmp.c",
            "target_symbol": "SMPmatSize",
            "indirect": False,
        },
    ],
}

KERNEL_FP_TABLES = frozenset({"src/maths/ni/niiter.c", "src/spicelib/analysis/cktload.c"})

# Plan Batch A: kernel + sparse + key headers — always overwrite summaries (source-grounded prose).
CURATED_SUMMARIES_BATCH_A: dict[str, str] = {
    "src/maths/ni/niiter.c": (
        "Top-level Newton-Raphson iteration for DC and transient analysis. Each pass clears/assembles the MNA "
        "system via `CKTload` (which indirectly dispatches every `DEVload`), applies sparse preorder/LU (`SMPreorder`/"
        "`SMPluFac`) and solve (`SMPsolve`), then checks convergence with `NIconvTest` against `CKTreltol`, `CKTvoltTol`, "
        "and `CKTabstol`. Optional node damping and UIC short-circuits are handled inside the main loop; callers such "
        "as `CKTop` layer gmin/source stepping outside this routine."
    ),
    "src/maths/ni/niconv.c": (
        "Implements `NIconvTest`, ngspice’s per-iteration NR convergence check after a linear solve: "
        "for each MNA row it compares `CKTrhs` vs `CKTrhsOld` using `CKTreltol` plus either `CKTvoltTol` "
        "(voltage nodes) or `CKTabstol` (current branches). On failure it records `CKTtroubleNode` for diagnostics. "
        "When built with `NEWCONV`, it may delegate to `CKTconvTest` for device-specific convergence tests."
    ),
    "src/maths/ni/niinteg.c": (
        "`NIintegrate` forms the companion-model linearization for a capacitor (or charge state) for the active "
        "integration method (`TRAPEZOIDAL` or `GEAR`) and order stored in `CKTcircuit`. It writes equivalent "
        "conductance `*geq` and Norton current `*ceq` from `CKTstate0` history using the `CKTag[]` coefficients "
        "computed by `NIcomCof` for the current timestep."
    ),
    "src/maths/ni/nicomcof.c": (
        "`NIcomCof` computes timestep-dependent integration coefficients (`CKTag[]`, and predictor tags `CKTagp[]` "
        "when `PREDICTOR` is enabled) for trapezoidal and multistep Gear correctors. It is the bridge between "
        "`CKTdelta` / `CKTdeltaOld[]` history and the stamps produced by `NIintegrate` and device transient loads."
    ),
    "src/maths/ni/nipred.c": (
        "`NIpred` extrapolates the next NR initial guess from past accepted timepoints (`CKTsols[][]`) using the "
        "active trapezoidal or Gear order; it sizes its loops with `SMPmatSize`. The body is compiled only when "
        "`PREDICTOR` is defined—otherwise the TU provides a stub."
    ),
    "src/spicelib/analysis/cktload.c": (
        "`CKTload` clears the sparse RHS, clears the MNA matrix with `SMPclear`, then walks every populated device "
        "type `i` and invokes `DEVices[i]->DEVload` when both the model list `CKThead[i]` and the `DEVload` hook "
        "exist. This is the central indirect dispatch point from the Newton kernel into all device families."
    ),
    "src/spicelib/analysis/dcop.c": (
        "`DCop` drives the DC operating-point analysis: it opens the DC plot, then calls `CKTop` to obtain a "
        "converged bias point (including gmin/source stepping fallbacks implemented inside `CKTop`). After success "
        "it reloads the linearized circuit with `CKTload` and dumps the OP snapshot to the frontend plot path."
    ),
    "src/spicelib/analysis/cktop.c": (
        "`CKTop` wraps the DC NR driver: it first attempts `NIiter` under the requested init/float modes; on "
        "non-convergence it optionally runs `dynamic_gmin`/`spice3_gmin` and then `gillespie_src`/`spice3_src` "
        "source-stepping ladders based on `CKTnumGminSteps`/`CKTnumSrcSteps`. Also hosts `CKTconvTest` when enabled."
    ),
    "src/spicelib/analysis/dctran.c": (
        "`DCtran` is the transient analysis driver: it advances simulated time, invokes predictor/corrector stages, "
        "calls `NIiter` for the inner NR solve at each candidate timepoint, accepts or rejects steps via `CKTaccept`, "
        "and asks devices for LTE via `CKTtrunc` to resize `CKTdelta`. Device loads reach `NIintegrate` for dynamic elements."
    ),
    "src/spicelib/analysis/acan.c": (
        "`ACan` performs small-signal AC: it ensures a converged DC bias (`CKTop` + `CKTload` as needed), switches "
        "the circuit into AC mode, then repeatedly calls `NIacIter` which factors/solves the complex Jacobian via "
        "`CKTacLoad` → `DEVices[]->DEVacLoad` for each frequency point."
    ),
    "src/maths/sparse/spfactor.c": (
        "Sparse LU factorization core for ngspice’s SMP matrix: builds elimination schedules, applies partial "
        "pivoting with circuit-provided tolerances, and diagnoses structural singularities that surface as pivot "
        "failures during `SMPluFac`/`SMPreorder`."
    ),
    "src/maths/sparse/spsolve.c": (
        "Sparse forward/back substitution (`SMPsolve` family) that applies the factored MNA to the current RHS "
        "vector after `SMPluFac` or complex AC factorization, producing Newton corrections or AC phasor unknowns."
    ),
    "src/maths/sparse/spbuild.c": (
        "Matrix construction helpers that allocate and populate the sparse MNA structure before factorization: "
        "binds stamps from `CKTload` into the SMP matrix representation used by the NI kernel."
    ),
    "src/maths/sparse/spsmp.c": (
        "SMP façade over the sparse package: exposes `SMPluFac`, `SMPsolve`, `SMPcLUfac`, `SMPcSolve`, `SMPmatSize`, "
        "and reordering entry points wired from `NIiter`/`NIacIter` and related analysis drivers."
    ),
    "src/include/ngspice/devdefs.h": (
        "Defines the `SPICEdev` device plugin contract: per-model/instance sizes, public name, and the function-pointer "
        "table (`DEVload`, `DEVacLoad`, `DEVtrunc`, `DEVsetup`, …) that `CKTload` and analysis code dispatch through."
    ),
    "src/include/ngspice/ifsim.h": (
        "Frontend/simulator interface typedefs (`IFsimulator`, `IFuid`, analysis job descriptors) connecting the "
        "nutmeg/frontend layer to the core `CKTcircuit` engine."
    ),
    "src/include/ngspice/iferrmsg.h": (
        "Canonical simulator error codes (`E_SINGULAR`, `E_ITERLIM`, `E_NOCONV`, …) returned from analysis, "
        "parser, and matrix layers for uniform reporting."
    ),
    "src/include/ngspice/trandefs.h": (
        "Transient integration enums/flags (`TRAPEZOIDAL`, `GEAR`, predictor bits) shared between NI integration "
        "routines and transient drivers such as `DCtran`."
    ),
    "src/include/ngspice/sperror.h": (
        "Sparse-specific error codes returned from SMP/sparse factor and solve routines, complementing `iferrmsg.h`."
    ),
}

def parse_front_matter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---"):
        return {}, text
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", text, re.DOTALL)
    if not m:
        return {}, text
    meta = yaml.safe_load(m.group(1)) or {}
    body = text[m.end() :]
    return meta, body


def first_body_summary(body: str, max_len: int = 450) -> str:
    """First substantive paragraph after title line."""
    lines = body.splitlines()
    buf: list[str] = []
    in_para = False
    for line in lines:
        s = line.strip()
        if s.startswith("#"):
            continue
        if s.startswith("```"):
            break
        if not s:
            if in_para and buf:
                break
            continue
        if s.startswith("<!--"):
            continue
        if s.startswith("["):
            continue
        in_para = True
        buf.append(s)
        if len(" ".join(buf)) >= max_len:
            break
    out = " ".join(buf).strip()
    if len(out) > max_len:
        out = out[: max_len - 3].rsplit(" ", 1)[0] + "..."
    return out or "Curated ngspice_book section (see path)."


def job_relevance_from_meta(meta: dict[str, Any]) -> dict[str, str]:
    mp = meta.get("mission_primary") or "circuit_design_validation"
    if mp == "kernel_reimplementation":
        return {"kernel_reimplementation": "high", "circuit_design_validation": "medium"}
    return {"kernel_reimplementation": "low", "circuit_design_validation": "high"}


def book_importance(meta: dict[str, Any], rel_path: str) -> float:
    if rel_path.endswith("README.md"):
        return 0.62
    ch = str(meta.get("chapter", ""))
    if ch in ("23_canonical_chains_reference", "22_nodalai_kernel_reimplementation", "02_numerical_kernel_core"):
        return 0.94
    if ch.startswith("20_") or ch.startswith("14_") or ch.startswith("18_"):
        return 0.88
    return 0.82


def build_book_docs() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for md in sorted(BOOK_ROOT.rglob("*.md")):
        rel = md.relative_to(REPO_ROOT).as_posix()
        text = md.read_text(encoding="utf-8", errors="replace")
        meta, body = parse_front_matter(text)
        title = meta.get("title") or md.stem.replace("_", " ")
        summary = first_body_summary(body)
        related = list(meta.get("related_files") or [])
        chains = list(meta.get("canonical_chain_tags") or [])
        concepts = list(meta.get("domain_concepts") or [])
        out.append(
            {
                "path": rel,
                "category": "curated_prose",
                "language": "markdown",
                "subsystem": "documentation",
                "title": title,
                "chapter": meta.get("chapter"),
                "section": meta.get("section"),
                "section_number": meta.get("section_number"),
                "job_relevance": job_relevance_from_meta(meta),
                "mission_primary": meta.get("mission_primary"),
                "mission_secondary": meta.get("mission_secondary") or [],
                "related_source_files": related,
                "canonical_chain_tags": chains,
                "domain_concepts": concepts,
                "summary": summary,
                "chunking_strategy": "semantic_section",
                "max_chunk_tokens": 1000,
                "chunk_overlap_tokens": 100,
                "importance_score": book_importance(meta, rel),
                "query_hints": [
                    f"ngspice book: {title}",
                    f"explain {title} in ngspice",
                ],
                "audience": meta.get("audience") or [],
                "estimated_reading_minutes": meta.get("estimated_reading_minutes"),
            }
        )
    return out


def load_attribution() -> dict[str, list[str]]:
    data = json.loads(ATTRIBUTION_PATH.read_text(encoding="utf-8"))
    return dict(data.get("attributions") or {})


def cross_link_sources(files: list[dict[str, Any]], attribution: dict[str, list[str]]) -> None:
    by_path = {e["path"]: e for e in files}
    for src, books in attribution.items():
        ent = by_path.get(src)
        if not ent:
            continue
        rf = list(dict.fromkeys((ent.get("related_files") or []) + books))
        ent["related_files"] = rf


def apply_cktdefs_constants(files: list[dict[str, Any]]) -> None:
    for ent in files:
        if ent.get("path") == "src/include/ngspice/cktdefs.h":
            ent["numerical_constants_defined"] = [dict(x) for x in CKTDEFS_H_NUMERICAL_METADATA]
            break


def purpose_label(purpose: str | None) -> str:
    mapping = {
        "nr_loop": "Newton-Raphson iteration",
        "device_load": "device MNA stamping (DEVload)",
        "device_acload": "AC small-signal stamping (DEVacLoad)",
        "integration_method": "numerical integration / companion models",
        "sparse_factor": "sparse LU factorization",
        "sparse_solve": "sparse linear solve",
        "netlist_parser": "netlist parsing",
        "command_interpreter": "nutmeg / interactive commands",
        "regression_test": "regression test netlist",
        "example_circuit": "example circuit",
        "documentation": "documentation",
        "utility": "supporting utility",
    }
    if not purpose:
        return "circuit simulation support"
    return mapping.get(purpose, purpose.replace("_", " "))


def subsystem_label(sub: str | None) -> str:
    if not sub:
        return "ngspice"
    return sub.replace("_", " ")


def extract_file_comment_head(text: str, max_chars: int = 500) -> str | None:
    """First block comment after includes (rough)."""
    # Strip leading blank and grab /* */ or first lines
    m = re.search(r"/\*([^*]|\*[^/])*\*/", text[:8000], re.DOTALL)
    if m:
        block = re.sub(r"\s+", " ", m.group(0)).strip("/* ").strip()
        if len(block) > max_chars:
            block = block[: max_chars - 3].rsplit(" ", 1)[0] + "..."
        if len(block) > 40:
            return block
    return None


def _dev_symbol_defined_in_tu(sym: str, text: str) -> bool:
    """True if `sym(` is defined in this .c file (not merely declared extern)."""
    if re.search(rf"^\s*extern\b.{{0,200}}{re.escape(sym)}\s*\(", text, re.MULTILINE | re.DOTALL):
        return False
    if re.search(rf"^{re.escape(sym)}\s*\(", text, re.MULTILINE):
        return True
    return bool(
        re.search(rf"^\s*(?:static\s+)?\w+(?:\s+\*|\s+)\s*{re.escape(sym)}\s*\(", text, re.MULTILINE)
    )


def scan_helper_calls(text: str) -> list[str]:
    """Symbols referenced in source (for summary enrichment)."""
    found: set[str] = set()
    for sym in DEVSUP_FUNCS:
        if re.search(rf"\b{re.escape(sym)}\s*\(", text):
            found.add(sym)
    for sym in ANALYSIS_CALLEES:
        if re.search(rf"\b{re.escape(sym)}\s*\(", text):
            found.add(sym)
    return sorted(found)


def discover_device_edges(entry: dict[str, Any], text: str) -> list[dict[str, Any]]:
    """Outgoing calls from device load/ac/trunc files to devsup, NIintegrate, CKTterr, or TU-local DEV helpers."""
    path = entry["path"]
    kf = entry.get("key_functions_defined") or []
    sym_guess = Path(path).stem
    if kf and isinstance(kf[0], dict) and kf[0].get("name"):
        sym_guess = kf[0]["name"]
    edges: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for m in re.finditer(r"\b(DEV[A-Za-z0-9_]+|NIintegrate|CKTterr)\s*\(", text):
        callee = m.group(1)
        if callee in ANALYSIS_CALLEES:
            tf, ts = ANALYSIS_CALLEES[callee]
        elif callee.startswith("DEV") and callee in DEVSUP_FUNCS:
            tf, ts = DEVSUP_PATH, callee
        elif callee.startswith("DEV"):
            if _dev_symbol_defined_in_tu(callee, text):
                tf, ts = path, callee
            else:
                continue
        else:
            continue
        key = (sym_guess, tf, ts)
        if key in seen:
            continue
        seen.add(key)
        edges.append(
            {"symbol": sym_guess, "target_file": tf, "target_symbol": ts, "indirect": False}
        )
    return edges


def build_summary(entry: dict[str, Any], source_text: str | None) -> str:
    path = entry["path"]
    purpose = entry.get("purpose")
    sub = entry.get("subsystem")
    devfam = entry.get("device_family_directory")
    sdf = entry.get("spicedev_function_implemented") or []
    lang = entry.get("language", "c")
    kfuncs = entry.get("key_functions_defined") or []
    top_names = [k.get("name") for k in kfuncs[:4] if isinstance(k, dict) and k.get("name")]

    head = source_text and extract_file_comment_head(source_text)

    parts: list[str] = []
    if head and len(head) > 60:
        parts.append(head)

    if devfam and sdf:
        if any(x.startswith("DEV") for x in sdf):
            parts.append(
                f"SPICEdev vtable-related code in `{path}` for device family `{devfam}` "
                f"({', '.join(sdf)})."
            )
        else:
            parts.append(
                f"Device-layer file `{path}` for family `{devfam}` ({', '.join(sdf)})."
            )
    elif entry.get("subsystem") == "numerical_kernel":
        parts.append(
            f"Numerical kernel file `{path}` ({purpose_label(purpose)}): "
            f"part of ngspice's {subsystem_label(sub)} pipeline."
        )
    elif entry.get("subsystem") == "sparse_solver":
        parts.append(
            f"Sparse matrix file `{path}` ({purpose_label(purpose)}): "
            "implements ngspice's direct sparse linear algebra layer."
        )
    elif entry.get("subsystem") == "frontend_parser":
        parts.append(
            f"Frontend/parser file `{path}` ({purpose_label(purpose)}): "
            "handles netlist text, dot commands, or elaboration."
        )
    elif entry.get("subsystem") == "frontend_command":
        parts.append(
            f"Nutmeg/command file `{path}` ({purpose_label(purpose)}): "
            "interactive or scripted control of simulation runs and vectors."
        )
    elif entry.get("subsystem") == "regression_test":
        parts.append(
            f"Regression netlist `{path}`: canonical ngspice test case for validation."
        )
    elif entry.get("subsystem") == "example_circuit":
        parts.append(f"Example circuit `{path}`: illustrates typical ngspice usage.")
    elif lang == "header":
        parts.append(
            f"Header `{path}` ({subsystem_label(sub)}): type/struct definitions and "
            "interface contracts consumed across the simulator."
        )
    else:
        parts.append(
            f"ngspice source `{path}` ({subsystem_label(sub)}, {purpose_label(purpose)})."
        )

    # Avoid false positives in headers/docs (comments mention API names).
    helpers = (
        source_text
        and lang == "c"
        and entry.get("subsystem") not in ("include", "documentation")
        and scan_helper_calls(source_text)
    )
    if helpers:
        parts.append(f"Notable numerical helpers referenced: {', '.join(helpers)}.")

    if top_names:
        parts.append(f"Key entry symbols include: {', '.join(top_names)}.")

    out = " ".join(parts).strip()
    out = re.sub(r"\s+", " ", out)
    if len(out) > 1200:
        out = out[:1197] + "..."
    return out


def load_source_text(rel_path: str) -> str | None:
    p = REPO_ROOT / rel_path
    if not p.is_file():
        return None
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def should_rewrite_summary(ent: dict[str, Any], s: str) -> bool:
    if BOILERPLATE_RE.match(s.strip()):
        return True
    # Prior run could mis-tag headers with helper names from comments.
    if ent.get("subsystem") == "include" and "Notable numerical helpers referenced:" in s:
        return True
    return False


def apply_summaries(files: list[dict[str, Any]]) -> None:
    for ent in files:
        s = ent.get("summary") or ""
        if not should_rewrite_summary(ent, s):
            continue
        txt = load_source_text(ent["path"])
        ent["summary"] = build_summary(ent, txt)


def apply_dev_trunc_summaries(files: list[dict[str, Any]]) -> None:
    """Uniform, accurate summaries for every DEVtrunc implementation."""
    for ent in files:
        sdf = ent.get("spicedev_function_implemented") or []
        if "DEVtrunc" not in sdf:
            continue
        path = ent["path"]
        if not path.endswith(".c"):
            continue
        fam = ent.get("device_family_directory") or "device"
        kf = ent.get("key_functions_defined") or []
        fn = kf[0].get("name") if kf and isinstance(kf[0], dict) else Path(path).stem
        ent["summary"] = (
            f"`{fn}` implements `DEVtrunc` for the `{fam}` device family: evaluates local truncation / timestep "
            f"criteria (often via `CKTterr` on stored charges) and tightens the global `*timeStep` budget when the "
            f"model predicts an LTE violation."
        )


def apply_curated_batch_a_summaries(files: list[dict[str, Any]]) -> None:
    """Force plan-quality summaries for kernel/sparse/header Batch A paths."""
    by_path = {e["path"]: e for e in files}
    for path, text in CURATED_SUMMARIES_BATCH_A.items():
        ent = by_path.get(path)
        if ent:
            ent["summary"] = text
    ckt = by_path.get("src/include/ngspice/cktdefs.h")
    if ckt:
        ckt["summary"] = (
            "Defines `CKTcircuit`, the live simulation state: sparse MNA matrix, RHS/history vectors, tolerance fields "
            "(`CKTreltol`, `CKTabstol`, `CKTvoltTol`, `CKTchgtol`), GMIN/source-step controls, integration method/order, "
            "timestep history, statistics, and analysis job pointers. Numeric defaults are established in `CKTinit` "
            "(see `numerical_constants_defined` on this entry)."
        )


def apply_kernel_call_graphs(files: list[dict[str, Any]]) -> None:
    by_path = {e["path"]: e for e in files}
    for path, edges in KERNEL_CALL_GRAPHS.items():
        ent = by_path.get(path)
        if not ent:
            continue
        ent["call_graph_outgoing"] = list(edges)
        if path in KERNEL_FP_TABLES:
            ent["function_pointer_tables_referenced"] = ["DEVices[]"]


def apply_device_call_graphs(files: list[dict[str, Any]]) -> None:
    by_path = {e["path"]: e for e in files}
    for ent in files:
        sdf = ent.get("spicedev_function_implemented") or []
        if not sdf or not (set(sdf) & CALL_GRAPH_RELEVANT_SPICEDEV):
            continue
        path = ent["path"]
        if not path.endswith(".c"):
            continue
        txt = load_source_text(path)
        if not txt:
            continue
        edges = discover_device_edges(ent, txt)
        if not edges:
            continue
        # merge with existing (kernel files already set)
        existing = list(ent.get("call_graph_outgoing") or [])
        have = {(e.get("target_file"), e.get("target_symbol")) for e in existing}
        for e in edges:
            key = (e["target_file"], e["target_symbol"])
            if key not in have:
                existing.append(e)
                have.add(key)
        ent["call_graph_outgoing"] = existing


def apply_spice_roles_and_designer_topics(files: list[dict[str, Any]]) -> None:
    """Accurate `spice_analysis_role` / `circuit_designer_topic` from curated maps + path rules."""
    for f in files:
        p = f.get("path") or ""
        n = Path(p).name
        f["spice_analysis_role"] = spice_analysis_role_for(p, n)
        f["circuit_designer_topic"] = circuit_designer_topic_for(p, n)


def apply_device_model_kinds(files: list[dict[str, Any]]) -> None:
    """`device_model_kind` is accurate: set only for `devices/<family>/` sources; else null."""
    for f in files:
        fam = device_family_from_path(f["path"])
        if fam and fam in DEV_DIR_TO_KIND:
            f["device_model_kind"] = DEV_DIR_TO_KIND[fam]
        else:
            f["device_model_kind"] = None


def apply_numerical_constants_accurate(files: list[dict[str, Any]]) -> None:
    """Per-TU extraction (strict) + curated `cktdefs.h` applied afterward."""
    for f in files:
        path = f.get("path") or ""
        if path == "src/include/ngspice/cktdefs.h":
            continue
        lang = f.get("language") or "c"
        if lang not in ("c", "header"):
            f["numerical_constants_defined"] = []
            continue
        txt = load_source_text(path) or ""
        f["numerical_constants_defined"] = numerical_constants_for_translation_unit(
            path, lang, txt
        )


def apply_spicedev_implemented(files: list[dict[str, Any]]) -> None:
    for f in files:
        p = f.get("path") or ""
        if not p.startswith("src/spicelib/devices/") or not p.endswith(".c"):
            continue
        if f.get("language") != "c":
            continue
        name = Path(p).name
        txt = load_source_text(p) or ""
        f["spicedev_function_implemented"] = resolve_spicedev_implemented(name, p, txt)


def apply_spicedev_fill_nonnull(files: list[dict[str, Any]]) -> None:
    """Non-device files: always refresh synthetic tags so analysis/designer fields stay in sync."""
    for f in files:
        p = f.get("path") or ""
        if (
            p.startswith("src/spicelib/devices/")
            and p.endswith(".c")
            and f.get("language") == "c"
        ):
            continue
        f["spicedev_function_implemented"] = offdevice_spicedev_tags(
            f.get("subsystem") or "unknown",
            f.get("spice_analysis_role"),
            f.get("circuit_designer_topic"),
            f.get("language") or "c",
        )


def ensure_call_graph_list(files: list[dict[str, Any]]) -> None:
    for f in files:
        if f.get("call_graph_outgoing") is None:
            f["call_graph_outgoing"] = []


def bump_schema(data: dict[str, Any]) -> None:
    data["index_schema_version"] = "1.1"
    data["book_index_added_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def refresh_stats(data: dict[str, Any], book_docs: list[dict[str, Any]]) -> None:
    st = data.setdefault("stats", {})
    st["total_book_docs"] = len(book_docs)
    files = data["files"]
    st["files_with_nonempty_call_graph"] = sum(1 for f in files if f.get("call_graph_outgoing"))
    # recompute mission matrix roughly
    kh_dh = kh_dl = kl_dh = kl_dl = 0
    for f in files:
        jr = f.get("job_relevance") or {}
        k = jr.get("kernel_reimplementation", "low")
        d = jr.get("circuit_design_validation", "low")
        kh = k == "high"
        dh = d == "high"
        if kh and dh:
            kh_dh += 1
        elif kh and not dh:
            kh_dl += 1
        elif not kh and dh:
            kl_dh += 1
        else:
            kl_dl += 1
    st["breakdown_by_mission_relevance"] = {
        "kernel_high_design_high": kh_dh,
        "kernel_high_design_low": kh_dl,
        "kernel_low_design_high": kl_dh,
        "kernel_low_design_low": kl_dl,
    }


def run_upgrade() -> None:
    print("Loading rag_index.json ...")
    data = json.loads(RAG_PATH.read_text(encoding="utf-8"))
    files: list[dict[str, Any]] = data["files"]

    bump_schema(data)

    print("Applying spice_analysis_role and circuit_designer_topic ...")
    apply_spice_roles_and_designer_topics(files)

    print("Applying device_model_kind from DEV_DIR_TO_KIND ...")
    apply_device_model_kinds(files)

    print("Applying spicedev_function_implemented (devices/) ...")
    apply_spicedev_implemented(files)
    print("Ensuring spicedev_function_implemented non-empty (all files) ...")
    apply_spicedev_fill_nonnull(files)

    print("Normalizing call_graph_outgoing ...")
    ensure_call_graph_list(files)

    print("Building book_docs ...")
    book_docs = build_book_docs()
    data["book_docs"] = book_docs

    print("Cross-linking source files to book sections ...")
    attribution = load_attribution()
    cross_link_sources(files, attribution)

    print("Backfilling imported_by ...")
    backfill_imported_by_only(files)

    print("Backfilling numerical_constants_defined (accurate per translation unit) ...")
    apply_numerical_constants_accurate(files)

    print("Applying cktdefs.h numerical_constants_defined ...")
    apply_cktdefs_constants(files)

    print("Rewriting summaries (all boilerplate entries) ...")
    apply_summaries(files)

    print("Applying curated Batch A summaries (kernel/sparse/headers) ...")
    apply_curated_batch_a_summaries(files)

    print("Applying curated DEVtrunc summaries ...")
    apply_dev_trunc_summaries(files)

    print("Applying kernel call graphs ...")
    apply_kernel_call_graphs(files)

    print("Applying device DEVload/DEVacLoad/DEVtrunc call graphs ...")
    apply_device_call_graphs(files)

    print("Expanding call_graph_outgoing (includes, callees, anchors) ...")
    expand_call_graph_for_all_records(files, REPO_ROOT)

    refresh_stats(data, book_docs)

    print(f"Writing {RAG_PATH} ...")
    RAG_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Done.")


def main() -> None:
    ap = argparse.ArgumentParser(description="Upgrade ngspice rag_index.json")
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate inputs only; do not write rag_index.json",
    )
    args = ap.parse_args()
    if args.dry_run:
        data = json.loads(RAG_PATH.read_text(encoding="utf-8"))
        bd = build_book_docs()
        print(f"Would write: book_docs={len(bd)}, files={len(data['files'])}")
        return
    run_upgrade()


if __name__ == "__main__":
    main()
