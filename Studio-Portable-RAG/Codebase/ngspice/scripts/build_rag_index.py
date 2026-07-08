#!/usr/bin/env python3
"""
Two-pass ngspice RAG index generator.
Writes ../rag_index.json relative to repo root (ngspice/).
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent

EXCLUDE_SUFFIXES = {
    ".o",
    ".lo",
    ".la",
    ".a",
    ".so",
    ".dll",
    ".lib",
    ".obj",
    ".png",
    ".gif",
    ".pdf",
    ".zip",
    ".Plo",
}
EXCLUDE_DIR_PARTS = frozenset(
    {
        ".git",
        ".vscode",
        ".idea",
        "autom4te.cache",
        "visualc",
        "mingw",
        "wbtools",
        "cppdep",
        "tclscripts",
        "debian",
        "rpm",
        ".deps",
        ".libs",
        "plotting",
        "wdisp",
        "trannoise",
    }
)
EXCLUDE_FILENAMES = frozenset({"lex.yy.c", "winmain.c", "parse-bison.c"})

SKIP_FRONTEND_COM = frozenset(
    {"com_asciiplot.c", "com_gnuplot.c", "com_xgraph.c", "com_ghelp.c"}
)

NUMERICAL_INVARIANT_MAP: dict[str, list[str]] = {
    "niiter.c": ["newton_raphson_iteration", "convergence_test", "damped_newton"],
    "niconv.c": ["convergence_test"],
    "nicomcof.c": ["gear_integration_order_2_to_6", "trapezoidal_integration"],
    "niinteg.c": [
        "trapezoidal_integration",
        "gear_integration_order_2_to_6",
        "backward_euler_integration",
        "lte_timestep_control",
    ],
    "niditer.c": ["newton_raphson_iteration"],
    "nipred.c": ["lte_timestep_control"],
    "nipzmeth.c": ["pz_pole_zero_eigensystem"],
    "nisenre.c": ["sensitivity_adjoint"],
    "spfactor.c": ["sparse_lu_factorization", "sparse_partial_pivoting"],
    "spsolve.c": ["sparse_lu_factorization"],
    "spbuild.c": ["mna_matrix_assembly"],
    "spalloc.c": ["sparse_ordering_heuristic"],
    "spsmp.c": ["sparse_ordering_heuristic"],
    "sputils.c": ["matrix_singularity_detection"],
    "dcop.c": ["gmin_stepping", "source_stepping"],
    "cktop.c": ["gmin_stepping", "source_stepping", "pseudo_transient"],
    "dctran.c": [
        "lte_timestep_control",
        "breakpoint_handling",
        "charge_conserving_capacitor_stamp",
    ],
    "cktload.c": ["mna_matrix_assembly"],
    "ckttrunc.c": ["lte_timestep_control"],
    "cktdelt.c": ["lte_timestep_control"],
    "acan.c": ["ac_small_signal_linearization"],
    "noisean.c": ["noise_analysis_psd_integration"],
    "pzan.c": ["pz_pole_zero_eigensystem"],
    "distoan.c": ["distortion_volterra"],
    "tfanal.c": ["ac_small_signal_linearization"],
    "cktsens.c": ["sensitivity_adjoint"],
    "cktsetup.c": ["mna_matrix_assembly"],
    "cktic.c": ["mna_matrix_assembly"],
    "ckttemp.c": ["mna_matrix_assembly"],
    "limit.c": ["junction_voltage_limiting", "fet_voltage_limiting", "current_limiting"],
    "xpressn.c": ["behavioral_expression_evaluation", "parameter_substitution"],
    "spicenum.c": ["parameter_substitution"],
    "subckt.c": ["subcircuit_flat_expansion"],
    "inp.c": ["netlist_tokenization"],
    "dotcards.c": ["netlist_dot_dispatch"],
    "rawfile.c": ["raw_file_serialization"],
    "fourier.c": ["noise_analysis_psd_integration"],
    "vectors.c": ["output_vector_management"],
}

DEV_DIR_TO_KIND: dict[str, str | None] = {
    "bsim4": "mosfet_bsim4",
    "bsim4v5": "mosfet_bsim4",
    "bsim4v6": "mosfet_bsim4",
    "bsim4v7": "mosfet_bsim4",
    "bsim3": "mosfet_bsim3",
    "bsim3v0": "mosfet_bsim3",
    "bsim3v1": "mosfet_bsim3",
    "bsim3v32": "mosfet_bsim3",
    "bsim1": "mosfet_level1",
    "bsim2": "mosfet_level2",
    "mos1": "mosfet_level1",
    "mos2": "mosfet_level2",
    "mos3": "mosfet_level3",
    "mos6": "mosfet_level6",
    "mos9": "mosfet_level9",
    "ekv": "mosfet_ekv",
    "hisim2": "mosfet_hisim2",
    "hisimhv1": "mosfet_hisim_hv2",
    "bsimsoi": "mosfet_bsim3",
    "bsim3soi_dd": "mosfet_bsim3",
    "bsim3soi_fd": "mosfet_bsim3",
    "bsim3soi_pd": "mosfet_bsim3",
    "soi3": "mosfet_bsim3",
    "bjt": "bjt_gummel_poon",
    "vbic": "bjt_vbic",
    "hicum2": "bjt_hicum2",
    "nbjt": "cider_numerical_bjt",
    "nbjt2": "cider_numerical_bjt2",
    "jfet": "jfet_level1",
    "jfet2": "jfet_level2",
    "mes": "mesfet_curtice",
    "mesa": "mesfet_statz",
    "hfet1": "mesfet_hfet",
    "hfet2": "mesfet_hfet",
    "dio": "diode",
    "cap": "capacitor",
    "ind": "inductor_mutual",
    "res": "resistor",
    "vsrc": "vsrc",
    "isrc": "isrc",
    "vcvs": "vcvs",
    "vccs": "vccs",
    "ccvs": "ccvs",
    "cccs": "cccs",
    "asrc": "asrc_behavioral",
    "sw": "swit_voltage",
    "csw": "csw_current",
    "urc": "urc_uniform_rc",
    "tra": "tra_lossless",
    "ltra": "ltra_lossy",
    "txl": "txl_simple",
    "cpl": "transmission_line_general",
    "numd": "cider_numerical_1d",
    "numd2": "cider_numerical_2d",
    "numos": "cider_numerical_mos",
    "ndev": "cider_numerical_framework",
    "adms": "adms_behavioral",
}

# Longest suffix first (device implementation filename → SPICEdev vtable role(s))
SPICEDEV_SUFFIXES: list[tuple[str, list[str] | None]] = [
    ("cvtest.c", ["DEVconvTest"]),
    ("soachk.c", ["DEVsoaCheck"]),
    ("noise.c", ["DEVnoise"]),
    ("mpar.c", ["DEVmParam"]),
    ("param.c", ["DEVparam"]),
    ("parm.c", ["DEVparam"]),
    ("trunc.c", ["DEVtrunc"]),
    ("trun.c", ["DEVtrunc"]),
    ("pzld.c", ["DEVpzLoad"]),
    ("pzs.c", ["DEVpzSetup"]),
    ("pzl.c", ["DEVpzLoad"]),
    ("acld.c", ["DEVacLoad"]),
    ("acl.c", ["DEVacLoad"]),
    ("temp.c", ["DEVtemperature"]),
    ("getic.c", ["DEVsetic"]),
    ("mask.c", ["DEVmodAsk"]),
    ("mdel.c", ["DEVmDelete"]),
    ("dest.c", ["DEVdestroy"]),
    ("delete.c", ["DEVdelete"]),
    ("setup.c", ["DEVsetup"]),
    ("sset.c", ["DEVsetup"]),
    ("dset.c", ["DEVsetup"]),
    ("set.c", ["DEVsetup"]),
    ("disto.c", ["DEVdistortion"]),
    ("dist.c", ["DEVdisto"]),
    ("sens.c", ["DEVsens"]),
    ("sacl.c", ["DEVacLoad"]),
    ("sload.c", ["DEVsenLoad"]),
    ("sprt.c", ["DEVsenPrint"]),
    ("supd.c", ["DEVsenUpdate"]),
    ("acct.c", ["DEVaccept"]),
    ("fbr.c", ["DEVfindBranch"]),
    ("dump.c", ["DEVdump"]),
    ("check.c", ["DEVconvTest"]),
    ("nois.c", ["DEVnoise"]),
    ("conv.c", ["DEVconvTest"]),
    ("par.c", ["DEVparam"]),
    ("ask.c", ["DEVask"]),
    ("del.c", ["DEVdelete"]),
    ("load.c", ["DEVload"]),
    ("ld.c", ["DEVload"]),
    ("noi.c", ["DEVnoise"]),
]

# Top-level spicelib/devices/*.c registry / dispatch (not a per-model vtable slot)
DEVICES_SUBSYSTEM_GLUE_FILES: frozenset[str] = frozenset(
    {
        "dev.c",
        "devsup.c",
        "limit.c",
        "cktaccept.c",
        "cktask.c",
        "cktbindnode.c",
        "cktcrte.c",
        "cktfinddev.c",
        "cktinit.c",
        "cktsoachk.c",
    }
)

_SPICE_DEV_AGGREGATE_RE = re.compile(r"\bSPICEdev\s+\w+\s*=")
_IFPARM_TABLE_RE = re.compile(r"\bIFparm\s+\w+\s*\[")

# Per-file SPICE analysis kind for `src/spicelib/analysis/*.c` only. Shared `ckt*.c`
# infrastructure (matrix assembly, node tables, generic dispatch) → omitted (null).
# PSS driver was previously mislabeled as DC OP.
SPICE_ANALYSIS_ROLE_BY_BASENAME: dict[str, str] = {
    # AC
    "acan.c": "ac_small_signal",
    "acaskq.c": "ac_small_signal",
    "acsetp.c": "ac_small_signal",
    "cktacdum.c": "ac_small_signal",
    # Noise
    "noisean.c": "noise",
    "cktnoise.c": "noise",
    "naskq.c": "noise",
    "nsetparm.c": "noise",
    "nevalsrc.c": "noise",
    "ninteg.c": "noise",
    # Pole–zero
    "pzan.c": "pole_zero",
    "pzaskq.c": "pole_zero",
    "pzsetp.c": "pole_zero",
    "cktpzld.c": "pole_zero",
    "cktpzset.c": "pole_zero",
    "cktpzstr.c": "pole_zero",
    # Distortion (harmonic)
    "distoan.c": "distortion",
    "cktdisto.c": "distortion",
    "daskq.c": "distortion",
    "dsetparm.c": "distortion",
    "dloadfns.c": "distortion",
    "dkerproc.c": "distortion",
    # Transfer function
    "tfanal.c": "transfer_function",
    "tfaskq.c": "transfer_function",
    "tfsetp.c": "transfer_function",
    # Sensitivity
    "cktsens.c": "sensitivity",
    "sensaskq.c": "sensitivity",
    "senssetp.c": "sensitivity",
    "cktsgen.c": "sensitivity",
    # DC sweep / transfer curve
    "dctrcurv.c": "dc_sweep",
    "dctsetp.c": "dc_sweep",
    "dctaskq.c": "dc_sweep",
    # DC operating point
    "dcop.c": "op_dc_operating_point",
    "cktop.c": "op_dc_operating_point",
    "dcosetp.c": "op_dc_operating_point",
    "dcoaskq.c": "op_dc_operating_point",
    # Periodic steady-state (PSS)
    "dcpss.c": "periodic_steady_state",
    "pssinit.c": "periodic_steady_state",
    "pssaskq.c": "periodic_steady_state",
    "psssetp.c": "periodic_steady_state",
    # Transient
    "dctran.c": "transient",
    "traninit.c": "transient",
    "tranaskq.c": "transient",
    "transetp.c": "transient",
    "ckttrunc.c": "transient",
    "cktsetbk.c": "transient",
    "cktclrbk.c": "transient",
    "cktbkdum.c": "transient",
}

DESIGNER_TOPIC_MAP: dict[str, str] = {
    "inp.c": "netlist_grammar_devices",
    "inpcom.c": "netlist_grammar_devices",
    "dotcards.c": "netlist_grammar_dotcommands",
    "subckt.c": "subcircuit_definition",
    "xpressn.c": "parameter_substitution",
    "spicenum.c": "parameter_substitution",
    "runcoms.c": "control_block_scripting",
    "runcoms2.c": "control_block_scripting",
    "rawfile.c": "output_format_raw",
    "outitf.c": "output_format_text",
    "vectors.c": "vector_manipulation",
    "measure.c": "measure_command",
    "com_measure2.c": "measure_command",
    "com_plot.c": "plot_command",
    "com_display.c": "plot_command",
    "com_fft.c": "plot_command",
    "com_let.c": "vector_manipulation",
    "com_set.c": "option_directive",
    "com_option.c": "option_directive",
    "breakp.c": "convergence_aid_directive",
    "breakp2.c": "convergence_aid_directive",
}


def spice_analysis_role_for(rel: str, name: str) -> str | None:
    if not rel.startswith("src/spicelib/analysis/") or not name.endswith(".c"):
        return None
    return SPICE_ANALYSIS_ROLE_BY_BASENAME.get(name)


# Backend netlist/parser (`spicelib/parser`): one designer-facing topic per TU.
_INP2_DEVICE_LINE_PARSER_LETTERS = "bcdefghijklmnopqrstuvwyz"
PARSER_CIRCUIT_DESIGNER_TOPIC_BY_BASENAME: dict[str, str] = {
    "ifeval.c": "expression_tree_numeric_evaluation",
    "ifnewuid.c": "simulation_identifier_allocation",
    "inp2dot.c": "dot_command_line_parser_backend",
    **{
        f"inp2{c}.c": "device_instance_line_parser"
        for c in _INP2_DEVICE_LINE_PARSER_LETTERS
    },
    "inpaname.c": "name_and_alias_resolution",
    "inpapnam.c": "device_parameter_keyword_resolution",
    "inpcfix.c": "numeric_literal_normalization",
    "inpdomod.c": "model_card_parsing_and_dispatch",
    "inpdoopt.c": "options_card_to_task_binding",
    "inpdpar.c": "instance_parameter_parsing",
    "inperrc.c": "parser_error_recovery",
    "inperror.c": "parser_error_messages",
    "inpeval.c": "parameter_expression_evaluation",
    "inpfindl.c": "branch_current_name_resolution",
    "inpfindv.c": "node_voltage_name_resolution",
    "inpgmod.c": "model_table_growth",
    "inpgstr.c": "quoted_string_tokenization",
    "inpgtitl.c": "title_card_handling",
    "inpgtok.c": "lexer_get_token",
    "inpgval.c": "physical_numeric_value_parsing",
    "inpkmods.c": "model_type_registration_table",
    "inplist.c": "model_and_instance_linked_lists",
    "inplkmod.c": "model_definition_lookup",
    "inpmkmod.c": "model_object_instantiation",
    "inpmktmp.c": "temporary_model_string_buffering",
    "inppas1.c": "parse_pass_one_dot_model",
    "inppas2.c": "parse_pass_two_element_cards",
    "inppas3.c": "parse_pass_three_nodeset_ic",
    "inppname.c": "instance_parameter_by_name",
    "inpptree.c": "expression_parse_tree_builder",
    "inpptree-parser.c": "expression_grammar_parser_generated",
    "inpsymt.c": "parse_tree_symbol_table",
    "inptyplk.c": "mosfet_level_to_device_type",
    "ptfuncs.c": "parse_tree_builtin_functions",
    "sperror.c": "spicenum_error_string_table",
}


def circuit_designer_topic_for(rel: str, name: str) -> str | None:
    """User-facing netlist/UI topic; null when not a designer-oriented TU."""
    if rel == "src/sharedspice.c":
        return "shared_lib_api"
    if rel.startswith("src/frontend/") and name in DESIGNER_TOPIC_MAP:
        return DESIGNER_TOPIC_MAP[name]
    if rel.startswith("src/spicelib/parser/") and name.endswith(".c"):
        return PARSER_CIRCUIT_DESIGNER_TOPIC_BY_BASENAME.get(name)
    return None


IMPORTANCE_TABLE: dict[str, float] = {
    "niiter.c": 1.0,
    "cktload.c": 1.0,
    "dcop.c": 1.0,
    "dctran.c": 1.0,
    "devdefs.h": 1.0,
    "cktdefs.h": 1.0,
    "ifsim.h": 1.0,
    "spfactor.c": 0.97,
    "spsolve.c": 0.95,
    "spbuild.c": 0.95,
    "acan.c": 0.95,
    "noisean.c": 0.93,
    "pzan.c": 0.91,
    "cktop.c": 0.97,
    "niconv.c": 0.95,
    "niinteg.c": 0.95,
    "nicomcof.c": 0.93,
    "b4ld.c": 0.95,
    "bjtload.c": 0.92,
    "dioload.c": 0.88,
    "cktinit.c": 0.94,
    "cktsetup.c": 0.93,
    "ckttrunc.c": 0.93,
    "limit.c": 0.96,
    "iferrmsg.h": 0.88,
    "mos1load.c": 0.87,
    "mos2load.c": 0.87,
    "mos3load.c": 0.87,
    "b4acld.c": 0.87,
    "b4temp.c": 0.85,
    "b4set.c": 0.84,
    "b4noi.c": 0.83,
    "inp.c": 0.82,
    "dotcards.c": 0.82,
    "subckt.c": 0.82,
    "xpressn.c": 0.80,
    "spicenum.c": 0.78,
    "runcoms.c": 0.78,
    "outitf.c": 0.75,
    "rawfile.c": 0.75,
    "vectors.c": 0.75,
    "measure.c": 0.70,
    "com_measure2.c": 0.70,
    "sharedspice.c": 0.68,
    "fourier.c": 0.65,
}

IMPORTANCE_BY_SUBSYSTEM: dict[str, float] = {
    "numerical_kernel": 0.75,
    "device_model": 0.70,
    "sparse_solver": 0.80,
    "frontend_parser": 0.70,
    "frontend_command": 0.55,
    "frontend_output": 0.65,
    "frontend_measure": 0.68,
    "shared_lib_api": 0.65,
    "xspice_event": 0.50,
    "raw_file_io": 0.68,
    "regression_test": 0.45,
    "example_circuit": 0.35,
    "documentation": 0.25,
    "utility": 0.35,
    "build": 0.20,
    "include": 0.55,
}

SUMMARY_OVERRIDES: dict[str, str] = {
    "src/maths/ni/niiter.c": (
        "Top-level Newton-Raphson iteration for DC and transient analysis. "
        "Per call: invokes CKTload to assemble Jacobian+RHS via per-device DEVload dispatch, "
        "calls spFactor+spSolve for sparse LU, applies optional damping when iteration "
        "count exceeds threshold, then evaluates per-node RELTOL/ABSTOL/VNTOL/CHGTOL "
        "convergence. Returns OK on convergence or E_ITERLIM on failure. "
        "Implements damped Newton; callers handle GMIN/source-step fallback."
    ),
    "src/spicelib/analysis/cktload.c": (
        "CKTload: iterates over all circuit devices and dispatches to each device's "
        "DEVload function via DEVices[type]->DEVload function pointer. Zeroes RHS and "
        "clears matrix before each call. Accumulates GMIN conductance stamps if set. "
        "This is the single point of MNA matrix assembly and the most critical indirect "
        "dispatch in the kernel; reimplementors must replicate the DEVices[] table lookup."
    ),
    "src/spicelib/analysis/dcop.c": (
        "DC operating-point driver. Calls CKTop which attempts standard NIiter NR; "
        "on E_ITERLIM falls back to GMIN stepping (raises GMIN, repeats NR at each level, "
        "then lowers); then source stepping if GMIN fails. Returns E_NOCONV only after "
        "all fallback ladders exhausted. Entry point for .op analysis."
    ),
    "src/spicelib/devices/bsim4/b4ld.c": (
        "BSIM4 v4.8 charge-based MOSFET DEVload function (5600+ lines). Computes drain "
        "current Ids, threshold voltage Vth, transcapacitances Cgg/Cgd/Cgs/Cdd/Cds, and "
        "gate-tunneling currents from terminal voltages Vgs/Vds/Vbs. Stamps small-signal "
        "conductance matrix and current vector into MNA at four terminal nodes, with "
        "charge-conserving capacitance stamps for transient. Calls DEVfetlim to limit "
        "per-iteration voltage step. Single largest device load in the codebase."
    ),
    "src/spicelib/devices/limit.c": (
        "Implements the three canonical SPICE voltage limiters: DEVpnjlim (PN junction "
        "limits Vbe/Vbc step using critical voltage Vcrit), DEVfetlim (FET gate limits Vgs step), "
        "DEVlimvds (drain-source limits Vds step). These are the exact mathematical invariants "
        "that prevent Newton-Raphson divergence in device models; any reimplementation must "
        "reproduce them faithfully."
    ),
    "src/include/ngspice/devdefs.h": (
        "SPICEdev plugin contract: IFdevice/SPICEdev struct with virtual function pointers "
        "(DEVload, DEVacLoad, DEVpzLoad, DEVnoise, DEVtrunc, DEVconvTest, DEVlimit, "
        "DEVtemperature, DEVgetic, DEVask, DEVmodAsk, DEVparam, DEVmParam, DEVsetup, "
        "DEVunsetup, DEVdestroy, DEVmDelete, DEVsens, DEVdistortion). Declares DEVpnjlim, "
        "DEVfetlim, DEVlimvds. The single most important header for kernel reimplementation."
    ),
}

CALL_GRAPH_OVERRIDES: dict[str, list[dict[str, Any]]] = {
    "src/spicelib/analysis/cktload.c": [
        {
            "symbol": "CKTload",
            "target_file": "src/spicelib/devices/<various>",
            "target_symbol": "DEVload",
            "indirect": True,
            "note": "Dispatches via DEVices[type]->DEVload function pointer table",
        },
    ],
    "src/maths/ni/niiter.c": [
        {
            "symbol": "NIiter",
            "target_file": "src/spicelib/analysis/cktload.c",
            "target_symbol": "CKTload",
            "indirect": False,
        },
        {
            "symbol": "NIiter",
            "target_file": "src/maths/sparse/spfactor.c",
            "target_symbol": "spFactor",
            "indirect": False,
        },
        {
            "symbol": "NIiter",
            "target_file": "src/maths/sparse/spsolve.c",
            "target_symbol": "spSolve",
            "indirect": False,
        },
        {
            "symbol": "NIiter",
            "target_file": "src/maths/ni/niconv.c",
            "target_symbol": "NIconvTest",
            "indirect": False,
        },
    ],
    "src/spicelib/analysis/dcop.c": [
        {
            "symbol": "DCop",
            "target_file": "src/spicelib/analysis/cktop.c",
            "target_symbol": "CKTop",
            "indirect": False,
        },
        {
            "symbol": "DCop",
            "target_file": "src/maths/ni/niiter.c",
            "target_symbol": "NIiter",
            "indirect": False,
        },
    ],
}

INCLUDE_RE = re.compile(r'#\s*include\s+"([^"]+)"')
SYSTEM_INCLUDE_RE = re.compile(r'#\s*include\s+<([^>]+)>')
FUNC_RE = re.compile(
    r"^(?!static\s)(?!extern\s)(?!typedef\s)"
    r"([A-Za-z_][A-Za-z0-9_ *\t]+?)\s+"
    r"([A-Za-z_][A-Za-z0-9_]*)\s*"
    r"\([^)]*\)\s*\{",
    re.MULTILINE,
)
# Only #defines whose names are classic SPICE option tokens and whose value is a plain numeric literal.
SPICE_NUMERIC_DEFINE_NAMES: frozenset[str] = frozenset(
    {
        "RELTOL",
        "ABSTOL",
        "VNTOL",
        "CHGTOL",
        "GMIN",
        "ITL1",
        "ITL2",
        "ITL3",
        "ITL4",
        "ITL5",
        "TRTOL",
        "PIVREL",
        "PIVTOL",
        "PIVABSTOL",
    }
)

SPICE_DEFINE_LINE_RE = re.compile(
    r"^\s*#\s*define\s+([A-Z][A-Z0-9_]*)\b\s+(.+?)\s*$",
    re.MULTILINE,
)

CKTINIT_ASSIGN_RE = re.compile(
    r"\bsckt\s*->\s*(CKT[a-zA-Z][a-zA-Z0-9]*)\s*=\s*([^;]+);",
    re.MULTILINE,
)


def _numeric_literal_ok(s: str) -> bool:
    t = s.strip().split("//")[0].strip().rstrip("fFlL")
    return bool(
        re.match(r"^[-+]?(?:\d+\.?\d*|\d*\.\d+)(?:[eE][-+]?\d+)?$", t)
    )


# Curated: `CKTcircuit` tolerance / iteration / pivot / default-MOS fields documented in cktdefs.h
# with defaults assigned in CKTinit (cktinit.c). source_line ≈ struct member line in cktdefs.h.
CKTDEFS_H_NUMERICAL_METADATA: list[dict[str, Any]] = [
    {
        "name": "CKTgmin",
        "default_value": "1e-12",
        "purpose": "Minimum conductance shunting PN junctions (GMIN).",
        "source_line": 209,
        "init_source": "src/spicelib/devices/cktinit.c",
        "init_line": 48,
    },
    {
        "name": "CKTabstol",
        "default_value": "1e-12",
        "purpose": "Absolute branch current tolerance (ABSTOL).",
        "source_line": 198,
        "init_source": "src/spicelib/devices/cktinit.c",
        "init_line": 50,
    },
    {
        "name": "CKTreltol",
        "default_value": "1e-3",
        "purpose": "Relative tolerance for NR convergence (RELTOL).",
        "source_line": 201,
        "init_source": "src/spicelib/devices/cktinit.c",
        "init_line": 51,
    },
    {
        "name": "CKTchgtol",
        "default_value": "1e-14",
        "purpose": "Absolute charge tolerance (CHGTOL).",
        "source_line": 202,
        "init_source": "src/spicelib/devices/cktinit.c",
        "init_line": 52,
    },
    {
        "name": "CKTvoltTol",
        "default_value": "1e-6",
        "purpose": "Absolute voltage tolerance (VNTOL).",
        "source_line": 203,
        "init_source": "src/spicelib/devices/cktinit.c",
        "init_line": 53,
    },
    {
        "name": "CKTtrtol",
        "default_value": "7",
        "purpose": "Transient truncation error factor (TRTOL).",
        "source_line": 212,
        "init_source": "src/spicelib/devices/cktinit.c",
        "init_line": 54,
    },
    {
        "name": "CKTtranMaxIter",
        "default_value": "10",
        "purpose": "Transient NR iterations per timepoint (ITL4).",
        "source_line": 190,
        "init_source": "src/spicelib/devices/cktinit.c",
        "init_line": 60,
    },
    {
        "name": "CKTdcMaxIter",
        "default_value": "100",
        "purpose": "DC operating-point NR iteration limit (ITL1).",
        "source_line": 187,
        "init_source": "src/spicelib/devices/cktinit.c",
        "init_line": 61,
    },
    {
        "name": "CKTdcTrcvMaxIter",
        "default_value": "50",
        "purpose": "DC transfer-curve iteration limit (ITL2).",
        "source_line": 188,
        "init_source": "src/spicelib/devices/cktinit.c",
        "init_line": 62,
    },
    {
        "name": "CKTpivotAbsTol",
        "default_value": "1e-13",
        "purpose": "Absolute pivot threshold for sparse matrix factorization.",
        "source_line": 199,
        "init_source": "src/spicelib/devices/cktinit.c",
        "init_line": 66,
    },
    {
        "name": "CKTpivotRelTol",
        "default_value": "1e-3",
        "purpose": "Relative pivot threshold for sparse matrix factorization.",
        "source_line": 200,
        "init_source": "src/spicelib/devices/cktinit.c",
        "init_line": 67,
    },
    {
        "name": "CKTtemp",
        "default_value": "300.15",
        "purpose": "Operating temperature (Kelvin).",
        "source_line": 93,
        "init_source": "src/spicelib/devices/cktinit.c",
        "init_line": 68,
    },
    {
        "name": "CKTnomTemp",
        "default_value": "300.15",
        "purpose": "Nominal measurement temperature (Kelvin).",
        "source_line": 94,
        "init_source": "src/spicelib/devices/cktinit.c",
        "init_line": 69,
    },
    {
        "name": "CKTdefaultMosM",
        "default_value": "1",
        "purpose": "Default MOS instance parallel multiplier M.",
        "source_line": 224,
        "init_source": "src/spicelib/devices/cktinit.c",
        "init_line": 70,
    },
    {
        "name": "CKTdefaultMosL",
        "default_value": "1e-4",
        "purpose": "Default MOS channel length (meters).",
        "source_line": 225,
        "init_source": "src/spicelib/devices/cktinit.c",
        "init_line": 71,
    },
    {
        "name": "CKTdefaultMosW",
        "default_value": "1e-4",
        "purpose": "Default MOS channel width (meters).",
        "source_line": 226,
        "init_source": "src/spicelib/devices/cktinit.c",
        "init_line": 72,
    },
    {
        "name": "CKTdefaultMosAD",
        "default_value": "0",
        "purpose": "Default MOS drain diffusion area.",
        "source_line": 227,
        "init_source": "src/spicelib/devices/cktinit.c",
        "init_line": 73,
    },
    {
        "name": "CKTdefaultMosAS",
        "default_value": "0",
        "purpose": "Default MOS source diffusion area.",
        "source_line": 228,
        "init_source": "src/spicelib/devices/cktinit.c",
        "init_line": 74,
    },
    {
        "name": "CKTabsDv",
        "default_value": "0.5",
        "purpose": "Node damping: absolute voltage change limit between NR iterations.",
        "source_line": 257,
        "init_source": "src/spicelib/devices/cktinit.c",
        "init_line": 90,
    },
    {
        "name": "CKTrelDv",
        "default_value": "2.0",
        "purpose": "Node damping: relative voltage change limit between NR iterations.",
        "source_line": 258,
        "init_source": "src/spicelib/devices/cktinit.c",
        "init_line": 91,
    },
    {
        "name": "RELTOL_DEFAULT",
        "default_value": "1e-3",
        "purpose": "Alias: maps to CKTreltol default.",
        "source_line": 201,
        "init_source": "src/spicelib/devices/cktinit.c",
        "init_line": 51,
        "alias_of": "CKTreltol",
    },
    {
        "name": "ABSTOL_DEFAULT",
        "default_value": "1e-12",
        "purpose": "Alias: maps to CKTabstol default.",
        "source_line": 198,
        "init_source": "src/spicelib/devices/cktinit.c",
        "init_line": 50,
        "alias_of": "CKTabstol",
    },
    {
        "name": "VNTOL_DEFAULT",
        "default_value": "1e-6",
        "purpose": "Alias: maps to CKTvoltTol default.",
        "source_line": 203,
        "init_source": "src/spicelib/devices/cktinit.c",
        "init_line": 53,
        "alias_of": "CKTvoltTol",
    },
    {
        "name": "CHGTOL_DEFAULT",
        "default_value": "1e-14",
        "purpose": "Alias: maps to CKTchgtol default.",
        "source_line": 202,
        "init_source": "src/spicelib/devices/cktinit.c",
        "init_line": 52,
        "alias_of": "CKTchgtol",
    },
    {
        "name": "GMIN_DEFAULT",
        "default_value": "1e-12",
        "purpose": "Alias: maps to CKTgmin default.",
        "source_line": 209,
        "init_source": "src/spicelib/devices/cktinit.c",
        "init_line": 48,
        "alias_of": "CKTgmin",
    },
    {
        "name": "ITL1_DEFAULT",
        "default_value": "100",
        "purpose": "Alias: maps to CKTdcMaxIter default.",
        "source_line": 187,
        "init_source": "src/spicelib/devices/cktinit.c",
        "init_line": 61,
        "alias_of": "CKTdcMaxIter",
    },
    {
        "name": "ITL2_DEFAULT",
        "default_value": "50",
        "purpose": "Alias: maps to CKTdcTrcvMaxIter default.",
        "source_line": 188,
        "init_source": "src/spicelib/devices/cktinit.c",
        "init_line": 62,
        "alias_of": "CKTdcTrcvMaxIter",
    },
    {
        "name": "ITL4_DEFAULT",
        "default_value": "10",
        "purpose": "Alias: maps to CKTtranMaxIter default.",
        "source_line": 190,
        "init_source": "src/spicelib/devices/cktinit.c",
        "init_line": 60,
        "alias_of": "CKTtranMaxIter",
    },
]

CRITICAL_HEADERS = frozenset(
    {
        "devdefs.h",
        "cktdefs.h",
        "ifsim.h",
        "iferrmsg.h",
        "smpdefs.h",
        "trandefs.h",
        "typedefs.h",
        "dvec.h",
        "wordlist.h",
        "plot.h",
        "sperror.h",
        "sharedspice.h",
        "optdefs.h",
        "gendefs.h",
        "acdefs.h",
        "noisedef.h",
        "pzdefs.h",
    }
)


def path_has_excluded_part(p: Path) -> bool:
    return any(part in EXCLUDE_DIR_PARTS for part in p.parts)


def should_skip_path(p: Path, repo: Path) -> bool:
    if path_has_excluded_part(p):
        return True
    if p.suffix.lower() in EXCLUDE_SUFFIXES:
        return True
    if p.name in EXCLUDE_FILENAMES:
        return True
    return False


def count_lines(text: str) -> int:
    return text.count("\n") + (1 if text and not text.endswith("\n") else 0)


def count_sloc(text: str) -> int:
    n = 0
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("//") or s.startswith("/*") or s.startswith("*"):
            continue
        n += 1
    return n


def is_stub_file(text: str) -> bool:
    """Skip files with < 10 non-comment, non-blank lines."""
    return count_sloc(text) < 10


def resolve_ngspice_include(inc: str, repo: Path) -> str | None:
    if inc.startswith("ngspice/"):
        rel = Path("src/include") / inc
        if (repo / rel).is_file():
            return rel.as_posix()
    # device-local headers e.g. bsim4def.h
    return None


def resolve_include(inc: str, from_file: Path, repo: Path) -> str | None:
    r = resolve_ngspice_include(inc, repo)
    if r:
        return r
    cand = (from_file.parent / inc).resolve()
    try:
        cand.relative_to(repo.resolve())
    except ValueError:
        return None
    if cand.is_file():
        return cand.relative_to(repo.resolve()).as_posix()
    return None


def extract_includes(text: str, from_file: Path, repo: Path) -> tuple[list[str], list[str]]:
    internal: list[str] = []
    external: list[str] = []
    for m in INCLUDE_RE.finditer(text):
        inc = m.group(1)
        resolved = resolve_include(inc, from_file, repo)
        if resolved:
            internal.append(resolved)
        else:
            internal.append(inc)  # keep raw for traceability
    for m in SYSTEM_INCLUDE_RE.finditer(text):
        external.append(f"<{m.group(1)}>")
    return internal, external


def extract_functions(text: str, max_n: int = 15) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for m in FUNC_RE.finditer(text):
        name = m.group(2)
        line_start = text[: m.start()].count("\n") + 1
        sig = text[m.start() : m.end()].replace("\n", " ").strip()
        if name in {"if", "while", "for", "switch", "return"}:
            continue
        out.append(
            {
                "name": name,
                "kind": "function",
                "line_start": line_start,
                "line_end": line_start,
                "signature": sig[:500],
                "doc": None,
            }
        )
        if len(out) >= max_n:
            break
    return out


def parse_cktinit_numeric_assignments(text: str) -> list[dict[str, Any]]:
    """Literal numeric assignments to `sckt->CKT…` inside cktinit.c (CKTinit defaults)."""
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for m in CKTINIT_ASSIGN_RE.finditer(text):
        field = m.group(1)
        rhs = m.group(2).strip().split("//")[0].strip()
        if field in seen:
            continue
        if rhs in ("NULL", "FALSE", "TRUE"):
            continue
        if "(" in rhs or ")" in rhs:
            continue
        if not _numeric_literal_ok(rhs):
            continue
        seen.add(field)
        line_no = text[: m.start()].count("\n") + 1
        out.append(
            {
                "name": field,
                "default_value": rhs,
                "purpose": f"Assigned in CKTinit (`{field}` on `CKTcircuit`).",
                "source_line": line_no,
                "defined_in": "src/spicelib/devices/cktinit.c",
            }
        )
    out.sort(key=lambda r: r["source_line"])
    return out[:55]


def extract_spice_numeric_defines(text: str) -> list[dict[str, Any]]:
    """#define names in SPICE_NUMERIC_DEFINE_NAMES whose value is a single numeric literal."""
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for m in SPICE_DEFINE_LINE_RE.finditer(text):
        name = m.group(1)
        if name not in SPICE_NUMERIC_DEFINE_NAMES or name in seen:
            continue
        rest = m.group(2).strip()
        if rest.startswith("("):
            continue
        tok = rest.split()[0]
        if not _numeric_literal_ok(tok):
            continue
        seen.add(name)
        line_no = text[: m.start()].count("\n") + 1
        out.append(
            {
                "name": name,
                "default_value": tok,
                "purpose": f"#define {name} (SPICE-related numeric token)",
                "source_line": line_no,
            }
        )
    return out[:25]


def numerical_constants_for_translation_unit(
    rel: str, lang: str, text: str
) -> list[dict[str, Any]]:
    """
    Accurate per-file list: no synthetic fillers.
    - cktdefs.h → full curated CKTcircuit / CKTinit metadata (copy).
    - cktinit.c → parsed numeric `sckt->CKT… = …` assignments.
    - Other C/H → strict SPICE #define names with numeric values, or [].
    """
    if lang not in ("c", "header"):
        return []
    if rel == "src/include/ngspice/cktdefs.h":
        return [dict(row) for row in CKTDEFS_H_NUMERICAL_METADATA]
    if rel.endswith("cktinit.c") and "CKTinit" in text:
        parsed = parse_cktinit_numeric_assignments(text)
        if parsed:
            return parsed
    return extract_spice_numeric_defines(text)


def extract_numerical_constants(text: str) -> list[dict[str, Any]]:
    """Deprecated name; use `numerical_constants_for_translation_unit` with path/lang."""
    return extract_spice_numeric_defines(text)


def device_family_from_path(rel: str) -> str | None:
    parts = rel.split("/")
    if "devices" not in parts:
        return None
    i = parts.index("devices")
    if i + 1 >= len(parts):
        return None
    fam = parts[i + 1]
    if fam in {"Makefile", "Makefile.am", "Makefile.in"}:
        return None
    # Files directly under devices/ (cktinit.c, dev.c, …) are not a family folder
    if "." in fam:
        return None
    return fam


def spicedev_for_device_file(name: str) -> list[str] | None:
    """Suffix + top-level glue only (no file body); prefer `resolve_spicedev_implemented`."""
    ln = name.lower()
    if ln in DEVICES_SUBSYSTEM_GLUE_FILES:
        return ["devices_subsystem_glue"]
    for suf, funcs in SPICEDEV_SUFFIXES:
        if ln.endswith(suf):
            return funcs
    return None


def resolve_spicedev_implemented(name: str, rel: str, text: str) -> list[str] | None:
    """
    Classify `spicedev_function_implemented` for `src/spicelib/devices/**/*.c`.
    Suffix rules first, then light content checks for descriptor / helper files.
    """
    if not rel.startswith("src/spicelib/devices/") or not name.endswith(".c"):
        return None

    ln = name.lower()
    if ln in DEVICES_SUBSYSTEM_GLUE_FILES:
        return ["devices_subsystem_glue"]

    if ln.endswith("accept.c") and ln.startswith("ckt"):
        return ["devices_subsystem_glue"]

    for suf, funcs in SPICEDEV_SUFFIXES:
        if ln.endswith(suf):
            return funcs

    if ln.endswith("accept.c") and ln != "cktaccept.c":
        return ["DEVaccept"]

    if ln.endswith("init.c") and _SPICE_DEV_AGGREGATE_RE.search(text):
        return ["SPICEdev_aggregate"]

    if _IFPARM_TABLE_RE.search(text) and not _SPICE_DEV_AGGREGATE_RE.search(text):
        return ["IFdevice_parameter_tables"]

    if ln.endswith("eval.c"):
        return ["model_internal_equations"]

    if ln.endswith("geo.c"):
        return ["model_geometry_parasitics"]

    if ln.endswith("moscap.c"):
        return ["model_intrinsic_capacitance"]

    if ln.endswith("cap.c"):
        return ["model_terminal_capacitance"]

    if ln.endswith("misc.c"):
        return ["model_auxiliary_support"]

    if ln.endswith("ic.c") and re.search(r"\w+getic\s*\(\s*GENmodel", text):
        return ["DEVsetic"]

    return None


def offdevice_spicedev_tags(
    subsystem: str,
    analysis_role: str | None,
    designer_topic: str | None,
    lang: str,
) -> list[str]:
    """
    Non-empty `spicedev_function_implemented` for files that are not a single
    SPICEdev slot (kernel, frontend, headers, tests, netlists, etc.).
    """
    tags: list[str] = [f"off_device_subsystem:{subsystem}"]
    if analysis_role:
        tags.append(f"analysis_role:{analysis_role}")
    if designer_topic:
        tags.append(f"circuit_designer_topic:{designer_topic}")
    if lang == "header":
        tags.append("compilation_unit:header_declarations")
    elif lang == "netlist":
        tags.append("artifact:netlist_or_testbench")
    elif lang == "other":
        tags.append("artifact:misc_source")
    return tags[:10]


def subsystem_for_path(rel: str, lang: str) -> str:
    if rel.startswith("tests/"):
        if rel.endswith(".cir"):
            return "regression_test"
        return "regression_test"
    if rel.startswith("examples/"):
        return "example_circuit"
    if rel in {"README", "NEWS", "INSTALL", "ChangeLog"}:
        return "documentation"
    if rel.startswith("src/maths/ni/"):
        return "numerical_kernel"
    if rel.startswith("src/maths/sparse/"):
        return "sparse_solver"
    if rel.startswith("src/spicelib/analysis/"):
        return "numerical_kernel"
    if rel.startswith("src/spicelib/devices/"):
        if Path(rel).name in {
            "cktinit.c",
            "cktaccept.c",
            "cktload.c",
        }:
            return "numerical_kernel"
        return "device_model"
    if rel.startswith("src/spicelib/parser/"):
        return "frontend_parser"
    if rel.startswith("src/frontend/numparam/"):
        return "frontend_parser"
    if rel.startswith("src/frontend/parser/"):
        return "frontend_parser"
    if rel.startswith("src/frontend/"):
        if "measure" in rel or "com_measure" in rel:
            return "frontend_measure"
        if rel.endswith("rawfile.c"):
            return "raw_file_io"
        if rel.startswith("src/frontend/com_"):
            return "frontend_command"
        return "frontend_parser"
    if rel == "src/sharedspice.c":
        return "shared_lib_api"
    if rel.startswith("src/xspice/"):
        return "xspice_event"
    if rel.startswith("src/include/ngspice/"):
        return "include"
    if rel.startswith("src/misc/"):
        return "utility"
    if lang == "header" and "/devices/" in rel and rel.endswith(".h"):
        return "device_model"
    return "utility"


def category_for_path(rel: str, lang: str) -> str:
    if rel.startswith("tests/") or rel.startswith("examples/"):
        return "support"
    if rel.startswith("src/include/"):
        return "support"
    if rel in {"README", "NEWS", "INSTALL", "ChangeLog"}:
        return "support"
    if rel.startswith("src/misc/"):
        return "support"
    return "core_logic"


def job_relevance(rel: str, subsystem: str, name: str) -> dict[str, str]:
    kh, dh = "medium", "medium"
    if subsystem == "numerical_kernel":
        kh, dh = "high", "low"
    elif subsystem == "sparse_solver":
        kh, dh = "high", "low"
    elif subsystem == "device_model":
        if "load" in name or name.endswith("ld.c"):
            kh, dh = "high", "medium"
        else:
            kh, dh = "high", "low"
    elif subsystem in {"frontend_parser", "frontend_command", "frontend_measure", "raw_file_io"}:
        kh, dh = "medium", "high"
    elif subsystem == "regression_test":
        kh, dh = "high", "high"
    elif subsystem == "example_circuit":
        kh, dh = "low", "high"
    elif subsystem == "documentation":
        kh, dh = "low", "high"
    elif subsystem == "include":
        base = Path(rel).name
        if base in {"devdefs.h", "cktdefs.h", "ifsim.h", "smpdefs.h", "trandefs.h"}:
            kh, dh = "high", "low"
        elif base in {"iferrmsg.h", "sperror.h"}:
            kh, dh = "medium", "high"
        else:
            kh, dh = "medium", "medium"
    elif subsystem == "shared_lib_api":
        kh, dh = "low", "high"
    elif subsystem == "xspice_event":
        kh, dh = "medium", "low"
    elif subsystem == "utility":
        kh, dh = "low", "low"
    return {"kernel_reimplementation": kh, "circuit_design_validation": dh}


def purpose_for(rel: str, subsystem: str, name: str) -> str:
    if spice_analysis_role_for(rel, name) is not None:
        return "analysis_driver"
    if "niiter" in name or "niniter" in name:
        return "nr_loop"
    if name == "niconv.c":
        return "convergence_test"
    if name.startswith("niinteg") or name == "nicomcof.c":
        return "integration_method"
    if subsystem == "sparse_solver":
        if "factor" in name:
            return "sparse_factor"
        if "solve" in name:
            return "sparse_solve"
        return "sparse_ordering"
    if name == "limit.c":
        return "limiter"
    if subsystem == "device_model" and name.endswith("load.c"):
        return "device_load"
    if subsystem == "device_model" and "acld" in name:
        return "device_acload"
    if subsystem == "device_model" and "trunc" in name:
        return "device_trunc"
    if subsystem == "device_model" and ("noise" in name or "noi.c" in name):
        return "device_noise"
    if subsystem == "device_model" and "temp.c" in name:
        return "device_temperature"
    if subsystem == "device_model" and "par" in name:
        return "device_param"
    if subsystem == "frontend_parser" and "inp" in name:
        return "netlist_parser"
    if name == "dotcards.c":
        return "dotcmd_parser"
    if name == "subckt.c":
        return "subckt_expander"
    if "xpressn" in name or "spicenum" in name:
        return "param_substitution"
    if subsystem == "frontend_command":
        return "command_interpreter"
    if "runcoms" in name:
        return "control_block_runner"
    if "rawfile" in name:
        return "raw_file_io"
    if "measure" in name:
        return "measure_command"
    if subsystem == "include":
        return "data_structure_def" if "defs" in name else "interface_contract"
    if subsystem == "regression_test":
        return "regression_test"
    if subsystem == "example_circuit":
        return "example_circuit"
    return "utility"


def module_for(rel: str) -> str:
    parts = rel.split("/")
    if rel.startswith("src/spicelib/analysis/"):
        return "spicelib_analysis"
    if rel.startswith("src/spicelib/devices/"):
        fam = device_family_from_path(rel) or "devices_root"
        return f"spicelib_devices_{fam}"
    if rel.startswith("src/spicelib/parser/"):
        return "spicelib_parser"
    if rel.startswith("src/maths/sparse/"):
        return "sparse"
    if rel.startswith("src/maths/ni/"):
        return "maths_ni"
    if rel.startswith("src/frontend/"):
        return "frontend"
    if rel.startswith("src/include/ngspice/"):
        return "include"
    if rel.startswith("tests/"):
        return "tests"
    if rel.startswith("examples/"):
        return "examples"
    return "_".join(parts[:3]) if len(parts) >= 3 else "root"


def chunking_for(rel: str, name: str) -> dict[str, Any]:
    if name == "niiter.c":
        return {
            "chunking_strategy": "ast_function",
            "max_chunk_tokens": 1200,
            "chunk_overlap_tokens": 120,
            "preserve_together": [[1, 400]],
        }
    if name == "b4ld.c":
        return {
            "chunking_strategy": "by_spicedev_function",
            "max_chunk_tokens": 1200,
            "chunk_overlap_tokens": 100,
            "preserve_together": [[71, 5601]],
        }
    if name in {"b4mpar.c", "b4temp.c", "b4set.c"}:
        return {
            "chunking_strategy": "by_spicedev_function",
            "max_chunk_tokens": 1200,
            "chunk_overlap_tokens": 100,
            "preserve_together": [],
        }
    if name == "dotcards.c":
        return {
            "chunking_strategy": "per_dotcmd",
            "max_chunk_tokens": 800,
            "chunk_overlap_tokens": 80,
            "preserve_together": [],
        }
    if name.startswith("com_") and name.endswith(".c"):
        return {
            "chunking_strategy": "per_command",
            "max_chunk_tokens": 800,
            "chunk_overlap_tokens": 80,
            "preserve_together": [],
        }
    if rel.startswith("tests/") and rel.endswith(".cir"):
        return {
            "chunking_strategy": "per_test_case",
            "max_chunk_tokens": 600,
            "chunk_overlap_tokens": 60,
            "preserve_together": [],
        }
    if name == "cktdefs.h":
        return {
            "chunking_strategy": "semantic_section",
            "max_chunk_tokens": 1000,
            "chunk_overlap_tokens": 100,
            "preserve_together": [],
        }
    if name == "devdefs.h":
        return {
            "chunking_strategy": "whole_file",
            "max_chunk_tokens": 1200,
            "chunk_overlap_tokens": 0,
            "preserve_together": [],
        }
    if rel.endswith(".h"):
        return {
            "chunking_strategy": "whole_file",
            "max_chunk_tokens": 600,
            "chunk_overlap_tokens": 0,
            "preserve_together": [],
        }
    return {
        "chunking_strategy": "ast_function",
        "max_chunk_tokens": 800,
        "chunk_overlap_tokens": 80,
        "preserve_together": [],
    }


def query_hints_for(rel: str, name: str, subsystem: str) -> list[str]:
    base = Path(name).stem
    hints = [
        f"what does {name} do in ngspice",
        f"ngspice source file {rel}",
    ]
    if name == "niiter.c":
        hints = [
            "how does ngspice's Newton-Raphson loop work",
            "what is the convergence test in ngspice",
            "how does NIiter call per-device load functions",
            "what damping is applied to NR iterations in ngspice",
            "how does NIiter fall back to GMIN stepping",
        ]
    elif name == "b4ld.c":
        hints = [
            "how is BSIM4 drain current computed",
            "what charge stamps does BSIM4 produce for transient analysis",
            "how does BSIM4 handle voltage limiting per iteration",
            "what BSIM4 model parameters affect Ids most strongly",
        ]
    elif name == "dotcards.c":
        hints = [
            "what dot-commands does ngspice support",
            "how is .tran parsed",
            "what is the syntax for .options in ngspice",
        ]
    elif subsystem == "regression_test" and rel.endswith(".cir"):
        hints = [
            f"ngspice regression test {name}",
            "is there a regression test for this circuit topology",
        ]
    return hints[:7]


def related_files_for(rel: str) -> list[str]:
    # lightweight heuristics
    out: list[str] = []
    if "bsim4/b4ld.c" in rel:
        out = [
            "src/spicelib/devices/bsim4/b4temp.c",
            "src/spicelib/devices/bsim4/b4acld.c",
            "src/include/ngspice/devdefs.h",
        ]
    elif rel.endswith("niiter.c"):
        out = [
            "src/spicelib/analysis/cktload.c",
            "src/maths/ni/niconv.c",
            "src/spicelib/analysis/dcop.c",
            "src/include/ngspice/cktdefs.h",
        ]
    elif rel.endswith("dcop.c"):
        out = [
            "src/spicelib/analysis/cktop.c",
            "src/maths/ni/niiter.c",
            "src/spicelib/analysis/dctran.c",
        ]
    return out[:5]


def detect_language(p: Path) -> str:
    s = p.suffix.lower()
    if s == ".c":
        return "c"
    if s == ".h":
        return "header"
    if s == ".cir" or s == ".sp":
        return "netlist"
    if s in {".l"}:
        return "flex"
    if s in {".y"}:
        return "bison"
    if s in {".md"}:
        return "markdown"
    if s in {".sh"}:
        return "shell"
    if "Makefile" in p.name:
        return "makefile"
    return "other"


def collect_candidate_files(repo: Path) -> list[Path]:
    files: list[Path] = []

    def add_tree(root: Path, pattern: str = "**/*", *, ex_dirs: set[str] | None = None):
        ex_dirs = ex_dirs or set()
        if not root.is_dir():
            return
        for p in root.rglob(pattern):
            if not p.is_file():
                continue
            if any(x in p.parts for x in ex_dirs):
                continue
            if should_skip_path(p, repo):
                continue
            files.append(p)

    add_tree(repo / "src/maths/ni", "*.c")
    add_tree(repo / "src/maths/sparse", "*.c")
    for c in (repo / "src/maths/cmaths").glob("cmath*.c"):
        if c.is_file() and not should_skip_path(c, repo):
            files.append(c)

    add_tree(repo / "src/spicelib/analysis", "*.c")
    add_tree(repo / "src/spicelib/parser", "*.c")
    add_tree(repo / "src/spicelib/devices", "*.c")
    for h in (repo / "src/spicelib/devices").rglob("*defs.h"):
        if h.is_file() and not should_skip_path(h, repo):
            files.append(h)

    fe = repo / "src/frontend"
    ex_fe = {"plotting", "wdisp", "trannoise", "help"}
    if fe.is_dir():
        for p in fe.rglob("*"):
            if not p.is_file():
                continue
            if any(x in p.parts for x in ex_fe):
                continue
            if p.suffix != ".c":
                continue
            if p.name in SKIP_FRONTEND_COM or p.name in EXCLUDE_FILENAMES:
                continue
            if should_skip_path(p, repo):
                continue
            if p.name == "nupatest.c" and "numparam" in p.parts:
                continue
            files.append(p)

    add_tree(repo / "src/misc", "*.c")
    inc = repo / "src/include/ngspice"
    if inc.is_dir():
        for p in inc.glob("*.h"):
            if p.name in {"config.h"}:
                continue
            if should_skip_path(p, repo):
                continue
            if p.name in CRITICAL_HEADERS or p.name.endswith("defs.h"):
                files.append(p)

    add_tree(repo / "src/xspice/cm", "*.c")

    sp = repo / "src/sharedspice.c"
    if sp.is_file():
        files.append(sp)

    tests = repo / "tests"
    if tests.is_dir():
        for p in tests.rglob("*.cir"):
            if should_skip_path(p, repo):
                continue
            files.append(p)
        # reference outputs — cap to stay near plan file budget
        # Omit bulk reference outputs to keep index within 800–1500 files (plan target);
        # regression .cir files remain first-class. Re-enable by raising this cap.
        _ref_cap = 0
        if _ref_cap:
            refs = sorted(tests.rglob("reference/*"))
            refs = [p for p in refs if p.is_file() and not should_skip_path(p, repo)]
            refs = [p for p in refs if p.suffix in {".txt", ".standard", ".out", ""}]
            files.extend(refs[:_ref_cap])

    ex_dir = repo / "examples"
    if ex_dir.is_dir():
        ec = sorted(ex_dir.rglob("*.cir"))
        ec = [p for p in ec if not should_skip_path(p, repo)]
        files.extend(ec[:48])

    for doc in ["README", "NEWS", "INSTALL", "ChangeLog"]:
        dp = repo / doc
        if dp.is_file():
            files.append(dp)

    # de-dup
    seen: set[str] = set()
    out: list[Path] = []
    for p in files:
        try:
            rel = p.resolve().relative_to(repo.resolve()).as_posix()
        except ValueError:
            continue
        if rel not in seen:
            seen.add(rel)
            out.append(p)
    return out


def build_file_record(p: Path, repo: Path) -> dict[str, Any] | None:
    rel = p.resolve().relative_to(repo.resolve()).as_posix()
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    if p.suffix == ".c" and is_stub_file(text):
        return None

    lang = detect_language(p)
    name = p.name
    st = p.stat()
    raw = p.read_bytes()
    file_id = hashlib.sha1(raw).hexdigest()[:12]
    content_hash = "sha256:" + hashlib.sha256(raw).hexdigest()
    mtime = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat()

    subsystem = subsystem_for_path(rel, lang)
    category = category_for_path(rel, lang)
    fam = device_family_from_path(rel)

    numerical = NUMERICAL_INVARIANT_MAP.get(name)
    dev_kind: str | None
    if fam and fam in DEV_DIR_TO_KIND:
        dev_kind = DEV_DIR_TO_KIND[fam]
    else:
        dev_kind = None

    analysis_role = spice_analysis_role_for(rel, name)
    designer_topic = circuit_designer_topic_for(rel, name)

    spicedev = None
    if lang == "c" and rel.startswith("src/spicelib/devices/"):
        spicedev = resolve_spicedev_implemented(name, rel, text)
        if name == "b4ld.c":
            spicedev = ["DEVload"]
    if not spicedev:
        spicedev = offdevice_spicedev_tags(subsystem, analysis_role, designer_topic, lang)

    imp = IMPORTANCE_TABLE.get(name)
    if imp is None:
        imp = IMPORTANCE_BY_SUBSYSTEM.get(subsystem, 0.5)

    internal_includes, external_includes = extract_includes(text, p, repo)
    key_funcs = extract_functions(text) if lang == "c" else []

    summary = SUMMARY_OVERRIDES.get(rel)
    if summary is None:
        summary = (
            f"ngspice source at {rel}: {subsystem.replace('_', ' ')} component ({lang}). "
            f"See path and symbols for retrieval."
        )

    purpose = purpose_for(rel, subsystem, name)
    domain_concepts = [
        x
        for x in (numerical or [])
        if x
    ][:8]
    if not domain_concepts:
        domain_concepts = ["spice_simulation", subsystem]

    tags = [subsystem, lang]
    if fam:
        tags.append(fam)

    chunk = chunking_for(rel, name)

    fp_tables: list[str] = []
    if rel.endswith("devices/dev.c"):
        fp_tables.append("DEVices[]")
    if rel.endswith("cktload.c"):
        fp_tables.append("DEVices[]")

    call_graph = list(CALL_GRAPH_OVERRIDES.get(rel, []))

    nc_list = numerical_constants_for_translation_unit(rel, lang, text)

    rec: dict[str, Any] = {
        "path": rel,
        "file_id": file_id,
        "category": category,
        "language": lang,
        "loc": count_lines(text),
        "sloc_total": count_sloc(text),
        "size_bytes": st.st_size,
        "content_hash": content_hash,
        "last_modified": mtime,
        "job_relevance": job_relevance(rel, subsystem, name),
        "numerical_invariant_kind": numerical,
        "numerical_constants_defined": nc_list,
        "device_model_kind": dev_kind,
        "spicedev_function_implemented": spicedev,
        "spice_analysis_role": analysis_role,
        "circuit_designer_topic": designer_topic,
        "module": module_for(rel),
        "subsystem": subsystem,
        "header_pair": None,
        "device_family_directory": fam,
        "c_includes_internal": internal_includes,
        "key_functions_defined": key_funcs,
        "summary": summary,
        "purpose": purpose,
        "domain_concepts": domain_concepts[:8],
        "tags": tags[:5],
        "key_symbols": [
            {**k, "kind": k.get("kind", "function")} for k in key_funcs[:15]
        ],
        "imports_internal": internal_includes,
        "imports_external": external_includes[:40],
        "imported_by": [],
        "imported_by_count": 0,
        "call_graph_outgoing": call_graph,
        "function_pointer_tables_referenced": fp_tables,
        "chunking_strategy": chunk["chunking_strategy"],
        "max_chunk_tokens": chunk["max_chunk_tokens"],
        "chunk_overlap_tokens": chunk["chunk_overlap_tokens"],
        "preserve_together": chunk["preserve_together"],
        "importance_score": imp,
        "query_hints": query_hints_for(rel, name, subsystem),
        "related_files": related_files_for(rel),
        "canonical_chain_tags": [],
        "notes": None,
    }
    return rec


def pass2_imported_by(records: list[dict[str, Any]], repo: Path) -> None:
    inc_map: dict[str, list[str]] = defaultdict(list)
    indexed = {r["path"] for r in records}
    for r in records:
        for inc in r["c_includes_internal"]:
            if inc in indexed:
                inc_map[inc].append(r["path"])
            else:
                # try resolve ngspice/ includes already normalized in list
                alt = inc if inc.startswith("src/") else None
                if alt and alt in indexed:
                    inc_map[alt].append(r["path"])
    for r in records:
        path = r["path"]
        r["imported_by"] = sorted(set(inc_map.get(path, [])))
        r["imported_by_count"] = len(r["imported_by"])


def attach_chain_tags(records: list[dict[str, Any]], chains: list[dict[str, Any]]) -> None:
    tag_map: dict[str, list[str]] = defaultdict(list)
    for c in chains:
        cid = c["chain_id"]
        for m in c["canonical_members"]:
            tag_map[m].append(cid)
    by_path = {r["path"]: r for r in records}
    for r in records:
        r["canonical_chain_tags"] = sorted(set(tag_map.get(r["path"], [])))
    # Wildcard placeholder in chain members — not indexed; skip
    _ = by_path


def compute_stats(
    records: list[dict[str, Any]],
    scanned: int,
    excluded: int,
) -> dict[str, Any]:
    langs = Counter(r["language"] for r in records)
    subs = Counter(r["subsystem"] for r in records)
    dev_fam = Counter(
        r["device_family_directory"] for r in records if r["device_family_directory"]
    )
    inv_c = Counter()
    for r in records:
        for k in r["numerical_invariant_kind"] or []:
            inv_c[k] += 1
    sp_c = Counter()
    for r in records:
        for k in r["spicedev_function_implemented"] or []:
            sp_c[k] += 1

    mrel = Counter()
    for r in records:
        jr = r["job_relevance"]
        kh = jr["kernel_reimplementation"] == "high"
        dh = jr["circuit_design_validation"] == "high"
        key = (
            "kernel_high_design_high"
            if kh and dh
            else (
                "kernel_high_design_low"
                if kh and not dh
                else (
                    "kernel_low_design_high"
                    if not kh and dh
                    else "kernel_low_design_low"
                )
            )
        )
        mrel[key] += 1

    analysis_drivers = sum(1 for r in records if r.get("spice_analysis_role"))

    return {
        "total_files_scanned": scanned,
        "files_included": len(records),
        "files_excluded": excluded,
        "core_logic_count": sum(1 for r in records if r["category"] == "core_logic"),
        "support_count": sum(1 for r in records if r["category"] == "support"),
        "total_loc_indexed": sum(r["loc"] for r in records),
        "breakdown_by_language": dict(langs),
        "breakdown_by_subsystem": dict(subs),
        "breakdown_by_device_family_directory": dict(dev_fam),
        "breakdown_by_numerical_invariant_kind": dict(inv_c),
        "breakdown_by_spicedev_function_implemented": dict(sp_c),
        "breakdown_by_mission_relevance": dict(mrel),
        "total_devices_indexed": len({k for k in dev_fam if k}),
        "total_analysis_drivers": analysis_drivers,
        "total_canonical_chains": 0,  # filled by caller
        "total_regression_tests": sum(
            1 for r in records if r["subsystem"] == "regression_test" and r["path"].endswith(".cir")
        ),
    }


def canonical_chains_def() -> list[dict[str, Any]]:
    return [
        {
            "chain_id": "dc_operating_point_chain",
            "name": "DC operating-point computation, end-to-end",
            "description": "Parser through NIiter, CKTload, DEVload dispatch, sparse solve, convergence.",
            "mission": "kernel_reimplementation",
            "stages_traversed": [
                "netlist_parse",
                "circuit_init",
                "dcop_driver",
                "nr_iteration",
                "device_load",
                "limiter_apply",
                "matrix_factor",
                "matrix_solve",
                "convergence_test",
                "result_export",
            ],
            "canonical_members": [
                "src/frontend/inp.c",
                "src/spicelib/devices/cktinit.c",
                "src/spicelib/analysis/cktop.c",
                "src/spicelib/analysis/dcop.c",
                "src/maths/ni/niiter.c",
                "src/spicelib/analysis/cktload.c",
                "src/maths/sparse/spfactor.c",
                "src/maths/sparse/spsolve.c",
                "src/maths/ni/niconv.c",
            ],
            "representative_query": "walk me through how ngspice computes a DC operating point from a netlist",
            "common_failure_modes": [
                "Convergence failure: NR exceeds ITL1",
                "Singular matrix during sparse factor",
                "Limiter oscillation at PN junction",
            ],
            "importance": 1.0,
        },
        {
            "chain_id": "transient_step_chain",
            "name": "One transient timestep, LTE and acceptance",
            "description": "Integration, NR, truncation, timestep control.",
            "mission": "kernel_reimplementation",
            "stages_traversed": [
                "predictor",
                "device_load_with_charge",
                "nr_iteration",
                "lte_estimation",
                "step_accept_or_reject",
            ],
            "canonical_members": [
                "src/spicelib/analysis/dctran.c",
                "src/maths/ni/niiter.c",
                "src/maths/ni/niinteg.c",
                "src/spicelib/devices/cktaccept.c",
                "src/spicelib/analysis/ckttrunc.c",
            ],
            "representative_query": "how does ngspice control transient timestep size",
            "common_failure_modes": ["LTE blowup", "min step reached"],
            "importance": 1.0,
        },
        {
            "chain_id": "ac_analysis_chain",
            "name": "AC small-signal analysis",
            "mission": "kernel_reimplementation",
            "stages_traversed": ["dc_op_first", "linearization", "complex_solve_per_frequency"],
            "canonical_members": [
                "src/spicelib/analysis/acan.c",
                "src/spicelib/analysis/cktload.c",
            ],
            "description": "Linearized small-signal AC after DC op.",
            "representative_query": "how does AC analysis linearize the circuit",
            "common_failure_modes": ["DC op not converged"],
            "importance": 0.95,
        },
        {
            "chain_id": "device_load_dispatch_chain",
            "name": "SPICEdev DEVload dispatch",
            "mission": "kernel_reimplementation",
            "stages_traversed": ["cktload_dispatch", "devices_table_lookup", "devload_call"],
            "canonical_members": [
                "src/spicelib/analysis/cktload.c",
                "src/include/ngspice/devdefs.h",
                "src/spicelib/devices/dev.c",
                "src/spicelib/devices/bsim4/b4ld.c",
            ],
            "description": "CKTload iterates devices and calls DEVices[type]->DEVload.",
            "representative_query": "how does ngspice call each device's load function",
            "common_failure_modes": [],
            "importance": 0.99,
        },
        {
            "chain_id": "convergence_aid_chain",
            "name": "GMIN / source stepping fallbacks",
            "mission": "kernel_reimplementation",
            "stages_traversed": ["standard_nr", "gmin_step", "source_step"],
            "canonical_members": [
                "src/spicelib/analysis/dcop.c",
                "src/spicelib/analysis/cktop.c",
                "src/maths/ni/niiter.c",
            ],
            "description": "Fallback ladder when DC NR fails.",
            "representative_query": "what does ngspice do when DC analysis doesn't converge",
            "common_failure_modes": [],
            "importance": 0.95,
        },
        {
            "chain_id": "sparse_solve_chain",
            "name": "Sparse LU factor and solve",
            "mission": "kernel_reimplementation",
            "stages_traversed": ["build_or_clear", "factor", "solve"],
            "canonical_members": [
                "src/maths/sparse/spbuild.c",
                "src/maths/sparse/spfactor.c",
                "src/maths/sparse/spsolve.c",
            ],
            "description": "Partial-pivot LU and forward/back substitution.",
            "representative_query": "how does ngspice's sparse solver work",
            "common_failure_modes": [],
            "importance": 0.95,
        },
        {
            "chain_id": "netlist_to_simulation_chain",
            "name": "Netlist to simulation (user view)",
            "mission": "circuit_design_validation",
            "stages_traversed": [
                "tokenize",
                "dispatch_devices_dotcmds",
                "subckt_expand",
                "param_substitute",
                "ckt_init",
                "analysis_run",
            ],
            "canonical_members": [
                "src/frontend/inp.c",
                "src/spicelib/parser/inpdomod.c",
                "src/frontend/dotcards.c",
                "src/frontend/subckt.c",
                "src/frontend/numparam/xpressn.c",
                "src/spicelib/devices/cktinit.c",
            ],
            "description": "Frontend parsing through circuit construction.",
            "representative_query": "what happens when I run ngspice on my netlist",
            "common_failure_modes": [],
            "importance": 0.95,
        },
        {
            "chain_id": "convergence_failure_diagnosis_chain",
            "name": "Convergence failure diagnosis",
            "mission": "circuit_design_validation",
            "stages_traversed": ["error_message_emit", "user_remediation_options"],
            "canonical_members": [
                "src/include/ngspice/iferrmsg.h",
                "src/spicelib/analysis/dcop.c",
                "src/spicelib/analysis/dctran.c",
                "src/frontend/runcoms.c",
            ],
            "description": "Error codes and user-facing options for non-convergence.",
            "representative_query": "my circuit doesn't converge; what should I try",
            "common_failure_modes": [],
            "importance": 0.95,
        },
        {
            "chain_id": "measure_extraction_chain",
            "name": ".measure extraction",
            "mission": "circuit_design_validation",
            "stages_traversed": ["sim_complete", "measure_parse", "vector_walk"],
            "canonical_members": [
                "src/frontend/measure.c",
                "src/frontend/com_measure2.c",
            ],
            "description": "Post-simulation measurement on vectors.",
            "representative_query": "how do I extract rise time with .measure",
            "common_failure_modes": [],
            "importance": 0.85,
        },
        {
            "chain_id": "raw_output_consumption_chain",
            "name": "Raw file output",
            "mission": "circuit_design_validation",
            "stages_traversed": ["sim_complete", "raw_serialize"],
            "canonical_members": ["src/frontend/rawfile.c"],
            "description": "Serialization of simulation results to .raw.",
            "representative_query": "what is the format of ngspice's .raw output",
            "common_failure_modes": [],
            "importance": 0.85,
        },
        {
            "chain_id": "behavioral_source_eval_chain",
            "name": "Behavioral B-source and expressions",
            "mission": "kernel_reimplementation",
            "stages_traversed": ["expression_eval", "param_bind", "device_load"],
            "canonical_members": [
                "src/spicelib/devices/asrc/asrcload.c",
                "src/frontend/numparam/xpressn.c",
            ],
            "description": "ASRC device load with expression evaluation via numparam.",
            "representative_query": "how does ngspice evaluate B-source expressions",
            "common_failure_modes": [],
            "importance": 0.82,
        },
        {
            "chain_id": "subcircuit_expansion_chain",
            "name": "Subcircuit expansion",
            "mission": "circuit_design_validation",
            "stages_traversed": ["subckt_parse", "flatten", "param_expand"],
            "canonical_members": [
                "src/frontend/subckt.c",
                "src/spicelib/parser/inpdomod.c",
            ],
            "description": "Hierarchical .subckt flattening.",
            "representative_query": "how does ngspice expand subcircuits",
            "common_failure_modes": [],
            "importance": 0.88,
        },
        {
            "chain_id": "shared_lib_api_chain",
            "name": "Shared library API",
            "mission": "circuit_design_validation",
            "stages_traversed": ["shared_entry", "vectors_export"],
            "canonical_members": [
                "src/sharedspice.c",
                "src/include/ngspice/sharedspice.h",
            ],
            "description": "libngspice shared API surface.",
            "representative_query": "how to embed ngspice as a shared library",
            "common_failure_modes": [],
            "importance": 0.80,
        },
    ]


def missions_def() -> dict[str, Any]:
    return {
        "kernel_reimplementation": {
            "description": "NodalAI-style kernel reimplementation: exact algorithms and call chains.",
            "primary_chains": [
                "dc_operating_point_chain",
                "transient_step_chain",
                "ac_analysis_chain",
                "device_load_dispatch_chain",
                "convergence_aid_chain",
                "sparse_solve_chain",
            ],
            "primary_groups": [
                "nr_iteration_core",
                "circuit_load_dispatch",
                "sparse_matrix_factor_solve",
                "device_model_mosfet_bsim4",
            ],
        },
        "circuit_design_validation": {
            "description": "Netlist syntax, analyses, outputs, pitfalls.",
            "primary_chains": [
                "netlist_to_simulation_chain",
                "convergence_failure_diagnosis_chain",
                "measure_extraction_chain",
                "raw_output_consumption_chain",
            ],
            "primary_groups": [
                "netlist_parser_main",
                "netlist_parser_dotcmds",
                "regression_test_suite",
            ],
        },
    }


def glossary_def() -> list[dict[str, str]]:
    terms = [
        ("Modified Nodal Analysis (MNA)", "Core equation formulation for SPICE.", "numerical"),
        ("Newton-Raphson iteration", "Nonlinear DC/transient solve loop.", "numerical"),
        ("Jacobian", "Matrix of partial derivatives in NR.", "numerical"),
        ("Sparse LU factorization", "Direct sparse linear solve in ngspice.", "numerical"),
        ("RELTOL", "Relative convergence tolerance.", "numerical"),
        ("ABSTOL", "Absolute current tolerance.", "numerical"),
        ("VNTOL", "Absolute voltage tolerance.", "numerical"),
        ("CHGTOL", "Absolute charge tolerance.", "numerical"),
        ("ITL1", "DC NR iteration limit.", "numerical"),
        ("ITL2", "Transient NR iteration limit.", "numerical"),
        ("ITL4", "Transient total iteration limit.", "numerical"),
        ("GMIN", "Minimum conductance across junctions.", "numerical"),
        ("GMIN stepping", "Convergence aid ramping GMIN.", "numerical"),
        ("Source stepping", "Ramp independent sources for DC convergence.", "numerical"),
        ("Pseudo-transient", "DC convergence via artificial dynamics.", "numerical"),
        ("Trapezoidal integration", "Default integration method family.", "numerical"),
        ("Gear method", "Multistep stiffly stable integration.", "numerical"),
        ("LTE", "Local truncation error for timestep control.", "numerical"),
        ("Charge conservation", "Charge-based device stamping for transients.", "numerical"),
        ("DEVpnjlim", "PN junction voltage limiter.", "numerical"),
        ("DEVfetlim", "FET gate voltage limiter.", "numerical"),
        ("Damped Newton", "NR with damping factor on divergence.", "numerical"),
        ("Operating point", "DC solution before AC/transient.", "numerical"),
        ("SPICEdev", "Device virtual function table contract.", "device"),
        ("DEVload", "Stamp Y matrix and RHS for nonlinear branch.", "device"),
        ("DEVacLoad", "Small-signal AC stamping.", "device"),
        ("DEVtrunc", "LTE timestep truncation test.", "device"),
        ("BSIM4", "Industry-standard MOSFET model.", "device"),
        ("BSIM3", "Earlier BSIM MOS model.", "device"),
        ("Gummel-Poon BJT", "Classic BJT model.", "device"),
        ("VBIC", "Advanced compact BJT model.", "device"),
        ("Behavioral B-source", "Voltage/current source from expression.", "device"),
        ("Netlist", "Textual circuit description for SPICE.", "frontend"),
        ("Dot-command", "Line starting with . controlling analysis.", "frontend"),
        (".tran", "Transient analysis directive.", "frontend"),
        (".ac", "AC analysis directive.", "frontend"),
        (".measure", "Post-sim measurement directive.", "frontend"),
        (".subckt", "Hierarchical block definition.", "frontend"),
        (".control", "Interactive nutmeg script block.", "frontend"),
        ("Raw file", "Binary/ASCII simulation output vectors.", "frontend"),
        ("NodalAI", "Python kernel reimplementation target.", "bridge"),
        ("PySpice", "Python bindings consuming ngspice.", "bridge"),
        ("Regression test", "Canonical netlist + reference output.", "bridge"),
        ("Singular matrix", "Zero pivot / structural singularity in MNA.", "numerical"),
        ("Partial pivoting", "Pivot selection during sparse LU.", "numerical"),
        ("Transcapacitance", "Charge-based capacitance coupling in MOS models.", "device"),
        ("MOS Level 1/2/3", "Shichman-Hodges and refinements.", "device"),
        ("EKV MOSFET", "Charge-based MOS model (ekv device).", "device"),
        ("HiSIM", "Surface-potential MOS model family.", "device"),
        ("VCVS/VCCS", "Voltage/current controlled sources.", "device"),
        ("URC", "Uniform distributed RC line.", "device"),
        ("LTRA", "Lossy transmission line.", "device"),
        ("Initial conditions", ".ic and UIC handling.", "frontend"),
        ("Nodeset", ".nodeset for NR initial guess.", "frontend"),
        ("nutmeg", "ngspice interactive command interpreter.", "frontend"),
        ("Vector", "Named simulation result waveform container.", "frontend"),
        ("Save (.save)", "Directive to retain node/branch waveforms.", "frontend"),
        ("B-element expression", "Behavioral source algebraic expression.", "frontend"),
    ]
    return [{"term": t, "definition": d, "category": c} for t, d, c in terms]


def build_groups(records: list[dict[str, Any]], repo: Path) -> list[dict[str, Any]]:
    by_path = {r["path"] for r in records}

    def pick(prefix: str | None = None, names: list[str] | None = None) -> list[str]:
        out: list[str] = []
        if names:
            for n in names:
                if n in by_path:
                    out.append(n)
        if prefix:
            out.extend(sorted(p for p in by_path if p.startswith(prefix)))
        return sorted(set(out))

    groups_spec: list[dict[str, Any]] = [
        {
            "group_id": "nr_iteration_core",
            "name": "Newton-Raphson iteration core",
            "description": "NIiter, convergence test, integration helpers.",
            "domain_concepts": ["newton_raphson", "convergence_test", "lte_timestep_control"],
            "entry_points": ["src/maths/ni/niiter.c"],
            "importance": 0.98,
            "deps": ["circuit_load_dispatch"],
            "chains": ["dc_operating_point_chain", "transient_step_chain"],
            "mission": "kernel_reimplementation",
            "prefix": "src/maths/ni/",
        },
        {
            "group_id": "circuit_load_dispatch",
            "name": "CKTload and DEVload dispatch",
            "description": "Matrix assembly via per-device loads.",
            "domain_concepts": ["mna_modified_nodal_analysis", "sparse_lu_factorization"],
            "entry_points": ["src/spicelib/analysis/cktload.c"],
            "importance": 1.0,
            "deps": ["device_dispatch_contract"],
            "chains": ["device_load_dispatch_chain", "dc_operating_point_chain"],
            "mission": "kernel_reimplementation",
            "names": [
                "src/spicelib/analysis/cktload.c",
                "src/spicelib/devices/dev.c",
                "src/include/ngspice/devdefs.h",
            ],
        },
        {
            "group_id": "analysis_driver_dc_op",
            "name": "DC operating point drivers",
            "description": "DCop and CKTop with convergence aids.",
            "domain_concepts": ["gmin_stepping", "operating_point"],
            "entry_points": ["src/spicelib/analysis/dcop.c"],
            "importance": 0.97,
            "deps": ["nr_iteration_core"],
            "chains": ["dc_operating_point_chain", "convergence_aid_chain"],
            "mission": "kernel_reimplementation",
            "names": ["src/spicelib/analysis/dcop.c", "src/spicelib/analysis/cktop.c"],
        },
        {
            "group_id": "analysis_driver_transient",
            "name": "Transient analysis",
            "description": "DCtran, truncation, acceptance.",
            "domain_concepts": ["trapezoidal_integration", "lte_timestep_control"],
            "entry_points": ["src/spicelib/analysis/dctran.c"],
            "importance": 0.96,
            "deps": ["integration_methods"],
            "chains": ["transient_step_chain"],
            "mission": "kernel_reimplementation",
            "names": [
                "src/spicelib/analysis/dctran.c",
                "src/spicelib/analysis/ckttrunc.c",
                "src/spicelib/analysis/cktdelt.c",
                "src/spicelib/devices/cktaccept.c",
            ],
        },
        {
            "group_id": "sparse_matrix_factor_solve",
            "name": "Sparse solver",
            "description": "Build, factor, solve sparse MNA matrix.",
            "domain_concepts": ["sparse_lu_factorization", "partial_pivoting"],
            "entry_points": ["src/maths/sparse/spfactor.c"],
            "importance": 0.96,
            "deps": [],
            "chains": ["sparse_solve_chain"],
            "mission": "kernel_reimplementation",
            "prefix": "src/maths/sparse/",
        },
        {
            "group_id": "voltage_limiters",
            "name": "Voltage limiters",
            "description": "DEVpnjlim, DEVfetlim, DEVlimvds implementations.",
            "domain_concepts": ["junction_voltage_limit", "fet_voltage_limiting"],
            "entry_points": ["src/spicelib/devices/limit.c"],
            "importance": 0.95,
            "deps": [],
            "chains": ["device_load_dispatch_chain"],
            "mission": "kernel_reimplementation",
            "names": ["src/spicelib/devices/limit.c", "src/include/ngspice/devdefs.h"],
        },
        {
            "group_id": "device_dispatch_contract",
            "name": "Device registration",
            "description": "DEVices table and model init.",
            "domain_concepts": ["spicedev_contract"],
            "entry_points": ["src/spicelib/devices/dev.c"],
            "importance": 0.94,
            "deps": [],
            "chains": ["device_load_dispatch_chain"],
            "mission": "kernel_reimplementation",
            "names": ["src/spicelib/devices/dev.c", "src/include/ngspice/devdefs.h"],
        },
        {
            "group_id": "device_model_mosfet_bsim4",
            "name": "BSIM4 family",
            "description": "BSIM4 compact MOS model sources.",
            "domain_concepts": ["bsim4_charge_based_model"],
            "entry_points": ["src/spicelib/devices/bsim4/b4ld.c"],
            "importance": 0.96,
            "deps": ["device_dispatch_contract"],
            "chains": ["device_load_dispatch_chain"],
            "mission": "both",
            "prefix": "src/spicelib/devices/bsim4/",
        },
        {
            "group_id": "netlist_parser_main",
            "name": "Netlist parser",
            "description": "Primary netlist ingestion.",
            "domain_concepts": ["netlist_tokenization"],
            "entry_points": ["src/frontend/inp.c"],
            "importance": 0.82,
            "deps": [],
            "chains": ["netlist_to_simulation_chain"],
            "mission": "circuit_design_validation",
            "names": ["src/frontend/inp.c", "src/frontend/inpcom.c"],
            "extra_prefix": "src/spicelib/parser/",
        },
        {
            "group_id": "netlist_parser_dotcmds",
            "name": "Dot-command parser",
            "description": "Parsing of .op, .tran, etc.",
            "domain_concepts": ["netlist_dot_dispatch"],
            "entry_points": ["src/frontend/dotcards.c"],
            "importance": 0.82,
            "deps": ["netlist_parser_main"],
            "chains": ["netlist_to_simulation_chain"],
            "mission": "circuit_design_validation",
            "names": ["src/frontend/dotcards.c"],
        },
        {
            "group_id": "parameter_numparam",
            "name": "Numparam",
            "description": ".param and expression evaluation.",
            "domain_concepts": ["parameter_substitution"],
            "entry_points": ["src/frontend/numparam/xpressn.c"],
            "importance": 0.78,
            "deps": [],
            "chains": ["netlist_to_simulation_chain", "behavioral_source_eval_chain"],
            "mission": "both",
            "prefix": "src/frontend/numparam/",
        },
        {
            "group_id": "control_block_runner",
            "name": "Control / run commands",
            "description": ".control execution path.",
            "domain_concepts": ["dot_control_block"],
            "entry_points": ["src/frontend/runcoms.c"],
            "importance": 0.76,
            "deps": [],
            "chains": ["convergence_failure_diagnosis_chain"],
            "mission": "circuit_design_validation",
            "names": ["src/frontend/runcoms.c", "src/frontend/runcoms2.c"],
        },
        {
            "group_id": "output_raw_file_io",
            "name": "Raw output",
            "description": ".raw writer.",
            "domain_concepts": ["raw_file_format"],
            "entry_points": ["src/frontend/rawfile.c"],
            "importance": 0.74,
            "deps": [],
            "chains": ["raw_output_consumption_chain"],
            "mission": "circuit_design_validation",
            "names": ["src/frontend/rawfile.c"],
        },
        {
            "group_id": "output_measure",
            "name": "Measure",
            "description": ".measure implementation.",
            "domain_concepts": ["measure_extraction"],
            "entry_points": ["src/frontend/measure.c"],
            "importance": 0.72,
            "deps": [],
            "chains": ["measure_extraction_chain"],
            "mission": "circuit_design_validation",
            "names": ["src/frontend/measure.c", "src/frontend/com_measure2.c"],
        },
        {
            "group_id": "regression_test_suite",
            "name": "Regression tests",
            "description": "tests/**/*.cir and references.",
            "domain_concepts": ["regression_test"],
            "entry_points": [],
            "importance": 0.45,
            "deps": [],
            "chains": [],
            "mission": "both",
            "prefix": "tests/",
        },
        {
            "group_id": "shared_library_api",
            "name": "Shared library",
            "description": "libngspice entry.",
            "domain_concepts": ["shared_lib_api"],
            "entry_points": ["src/sharedspice.c"],
            "importance": 0.68,
            "deps": [],
            "chains": ["shared_lib_api_chain"],
            "mission": "circuit_design_validation",
            "names": ["src/sharedspice.c", "src/include/ngspice/sharedspice.h"],
        },
        {
            "group_id": "integration_methods",
            "name": "Integration methods",
            "description": "TRAP, Gear, BE in NI integrator.",
            "domain_concepts": ["trapezoidal_integration", "gear_method"],
            "entry_points": ["src/maths/ni/niinteg.c"],
            "importance": 0.94,
            "deps": ["nr_iteration_core"],
            "chains": ["transient_step_chain"],
            "mission": "kernel_reimplementation",
            "names": [
                "src/maths/ni/niinteg.c",
                "src/maths/ni/nicomcof.c",
                "src/maths/ni/nipred.c",
            ],
        },
        {
            "group_id": "data_structure_definitions",
            "name": "Core headers",
            "description": "CKTcircuit and interface structs.",
            "domain_concepts": ["mna_modified_nodal_analysis"],
            "entry_points": ["src/include/ngspice/cktdefs.h"],
            "importance": 0.90,
            "deps": [],
            "chains": ["dc_operating_point_chain"],
            "mission": "kernel_reimplementation",
            "names": [
                "src/include/ngspice/cktdefs.h",
                "src/include/ngspice/ifsim.h",
                "src/include/ngspice/smpdefs.h",
                "src/include/ngspice/trandefs.h",
                "src/include/ngspice/typedefs.h",
                "src/include/ngspice/dvec.h",
                "src/include/ngspice/wordlist.h",
                "src/include/ngspice/plot.h",
            ],
        },
        {
            "group_id": "error_message_catalog",
            "name": "Errors",
            "description": "Simulator error codes.",
            "domain_concepts": ["convergence_tolerance"],
            "entry_points": ["src/include/ngspice/iferrmsg.h"],
            "importance": 0.85,
            "deps": [],
            "chains": ["convergence_failure_diagnosis_chain"],
            "mission": "circuit_design_validation",
            "names": ["src/include/ngspice/iferrmsg.h", "src/include/ngspice/sperror.h"],
        },
        {
            "group_id": "device_model_xspice",
            "name": "XSPICE CM",
            "description": "Event-driven model core.",
            "domain_concepts": ["xspice_event"],
            "entry_points": ["src/xspice/cm/cm.c"],
            "importance": 0.50,
            "deps": [],
            "chains": [],
            "mission": "kernel_reimplementation",
            "prefix": "src/xspice/cm/",
        },
        {
            "group_id": "subcircuit_expander",
            "name": "Subcircuits",
            "description": "subckt expansion.",
            "domain_concepts": ["subcircuit_expansion"],
            "entry_points": ["src/frontend/subckt.c"],
            "importance": 0.80,
            "deps": [],
            "chains": ["subcircuit_expansion_chain", "netlist_to_simulation_chain"],
            "mission": "circuit_design_validation",
            "names": ["src/frontend/subckt.c"],
        },
        {
            "group_id": "analysis_driver_ac",
            "name": "AC analysis driver",
            "description": "Small-signal AC sweep driver.",
            "domain_concepts": ["ac_small_signal_linearization"],
            "entry_points": ["src/spicelib/analysis/acan.c"],
            "importance": 0.94,
            "deps": ["nr_iteration_core"],
            "chains": ["ac_analysis_chain"],
            "mission": "kernel_reimplementation",
            "names": ["src/spicelib/analysis/acan.c"],
        },
        {
            "group_id": "analysis_driver_noise",
            "name": "Noise analysis",
            "description": "Noise spectral density integration.",
            "domain_concepts": ["noise_analysis_psd_integration"],
            "entry_points": ["src/spicelib/analysis/noisean.c"],
            "importance": 0.90,
            "deps": [],
            "chains": [],
            "mission": "kernel_reimplementation",
            "names": ["src/spicelib/analysis/noisean.c"],
        },
        {
            "group_id": "analysis_driver_pz",
            "name": "Pole-zero analysis",
            "description": "Pole-zero eigenproblem driver.",
            "domain_concepts": ["pz_pole_zero_eigensystem"],
            "entry_points": ["src/spicelib/analysis/pzan.c"],
            "importance": 0.88,
            "deps": [],
            "chains": [],
            "mission": "kernel_reimplementation",
            "names": ["src/spicelib/analysis/pzan.c", "src/maths/ni/nipzmeth.c"],
        },
        {
            "group_id": "analysis_driver_sensitivity",
            "name": "Sensitivity analysis",
            "description": "Adjoint sensitivity support.",
            "domain_concepts": ["sensitivity_adjoint"],
            "entry_points": ["src/spicelib/analysis/cktsens.c"],
            "importance": 0.85,
            "deps": [],
            "chains": [],
            "mission": "kernel_reimplementation",
            "names": ["src/spicelib/analysis/cktsens.c", "src/maths/ni/nisenre.c"],
        },
        {
            "group_id": "device_model_bjt",
            "name": "BJT Gummel-Poon",
            "description": "Bipolar junction transistor compact model.",
            "domain_concepts": ["gummel_poon_bjt"],
            "entry_points": ["src/spicelib/devices/bjt/bjtload.c"],
            "importance": 0.88,
            "deps": ["device_dispatch_contract"],
            "chains": ["device_load_dispatch_chain"],
            "mission": "both",
            "prefix": "src/spicelib/devices/bjt/",
        },
        {
            "group_id": "device_model_diode",
            "name": "Diode",
            "description": "PN junction diode model.",
            "domain_concepts": ["junction_voltage_limit"],
            "entry_points": ["src/spicelib/devices/dio/dioload.c"],
            "importance": 0.86,
            "deps": ["device_dispatch_contract"],
            "chains": ["device_load_dispatch_chain"],
            "mission": "both",
            "prefix": "src/spicelib/devices/dio/",
        },
        {
            "group_id": "device_model_mos_levels_legacy",
            "name": "Legacy MOS levels 1–3,6,9",
            "description": "Classic SPICE MOS models.",
            "domain_concepts": ["mosfet_level1"],
            "entry_points": ["src/spicelib/devices/mos1/mos1load.c"],
            "importance": 0.82,
            "deps": ["device_dispatch_contract"],
            "chains": ["device_load_dispatch_chain"],
            "mission": "both",
            "prefixes": [
                "src/spicelib/devices/mos1/",
                "src/spicelib/devices/mos2/",
                "src/spicelib/devices/mos3/",
                "src/spicelib/devices/mos6/",
                "src/spicelib/devices/mos9/",
            ],
        },
        {
            "group_id": "device_model_passives",
            "name": "R L C",
            "description": "Linear passive elements.",
            "domain_concepts": ["mna_modified_nodal_analysis"],
            "entry_points": ["src/spicelib/devices/res/resload.c"],
            "importance": 0.78,
            "deps": ["device_dispatch_contract"],
            "chains": ["device_load_dispatch_chain"],
            "mission": "both",
            "prefixes": [
                "src/spicelib/devices/res/",
                "src/spicelib/devices/cap/",
                "src/spicelib/devices/ind/",
            ],
        },
        {
            "group_id": "device_model_sources_linear",
            "name": "Independent and linear controlled sources",
            "description": "V/I sources and EFGH elements.",
            "domain_concepts": ["vcvs_vccs_sources"],
            "entry_points": ["src/spicelib/devices/vsrc/vsrcload.c"],
            "importance": 0.78,
            "deps": ["device_dispatch_contract"],
            "chains": ["device_load_dispatch_chain"],
            "mission": "both",
            "prefixes": [
                "src/spicelib/devices/vsrc/",
                "src/spicelib/devices/isrc/",
                "src/spicelib/devices/vcvs/",
                "src/spicelib/devices/vccs/",
                "src/spicelib/devices/ccvs/",
                "src/spicelib/devices/cccs/",
            ],
        },
        {
            "group_id": "device_model_behavioral_asrc",
            "name": "ASRC behavioral sources",
            "description": "B-element / ASRC device family.",
            "domain_concepts": ["behavioral_source_b_element"],
            "entry_points": ["src/spicelib/devices/asrc/asrcload.c"],
            "importance": 0.80,
            "deps": ["device_dispatch_contract", "parameter_numparam"],
            "chains": ["behavioral_source_eval_chain", "device_load_dispatch_chain"],
            "mission": "both",
            "prefix": "src/spicelib/devices/asrc/",
        },
        {
            "group_id": "device_model_switches",
            "name": "Switches",
            "description": "Voltage and current controlled switches.",
            "domain_concepts": ["swit_voltage"],
            "entry_points": ["src/spicelib/devices/sw/swload.c"],
            "importance": 0.72,
            "deps": ["device_dispatch_contract"],
            "chains": ["device_load_dispatch_chain"],
            "mission": "both",
            "prefixes": [
                "src/spicelib/devices/sw/",
                "src/spicelib/devices/csw/",
            ],
        },
        {
            "group_id": "device_model_transmission_lines",
            "name": "Transmission lines",
            "description": "TRA, URC, LTRA, TXL, CPL.",
            "domain_concepts": ["tra_lossless"],
            "entry_points": ["src/spicelib/devices/tra/traload.c"],
            "importance": 0.72,
            "deps": ["device_dispatch_contract"],
            "chains": ["device_load_dispatch_chain"],
            "mission": "both",
            "prefixes": [
                "src/spicelib/devices/tra/",
                "src/spicelib/devices/urc/",
                "src/spicelib/devices/ltra/",
                "src/spicelib/devices/txl/",
                "src/spicelib/devices/cpl/",
            ],
        },
        {
            "group_id": "expression_parser_frontend",
            "name": "Frontend expression lexer/parser",
            "description": "nutmeg/parser lexical layer.",
            "domain_concepts": ["expression_evaluator"],
            "entry_points": ["src/frontend/parser/lexical.c"],
            "importance": 0.62,
            "deps": [],
            "chains": [],
            "mission": "circuit_design_validation",
            "prefix": "src/frontend/parser/",
        },
        {
            "group_id": "documentation_bundle",
            "name": "Top-level documentation",
            "description": "README, NEWS, install notes.",
            "domain_concepts": ["documentation"],
            "entry_points": [],
            "importance": 0.25,
            "deps": [],
            "chains": [],
            "mission": "circuit_design_validation",
            "names": ["README", "NEWS", "INSTALL", "ChangeLog"],
        },
        {
            "group_id": "example_circuits_per_analysis",
            "name": "Example circuits",
            "description": "Representative example netlists.",
            "domain_concepts": ["example_circuit"],
            "entry_points": [],
            "importance": 0.35,
            "deps": [],
            "chains": [],
            "mission": "circuit_design_validation",
            "prefix": "examples/",
        },
    ]

    out: list[dict[str, Any]] = []
    for spec in groups_spec:
        files: list[str] = []
        if spec.get("names"):
            files.extend(pick(names=spec["names"]))
        if spec.get("prefix"):
            files.extend(pick(prefix=spec["prefix"]))
        for pr in spec.get("prefixes") or []:
            files.extend(pick(prefix=pr))
        if spec.get("extra_prefix"):
            files.extend(pick(prefix=spec["extra_prefix"]))
        files = sorted(set(files))
        entry = [e for e in spec["entry_points"] if e in by_path]
        out.append(
            {
                "group_id": spec["group_id"],
                "name": spec["name"],
                "description": spec["description"],
                "domain_concepts": spec["domain_concepts"],
                "entry_points": entry or spec["entry_points"],
                "files": files,
                "group_importance": spec["importance"],
                "cross_group_dependencies": spec["deps"],
                "canonical_chain_tags": spec["chains"],
                "mission_emphasis": spec["mission"],
            }
        )
    return out


CALLEE_SCAN_SKIP = frozenset(
    {
        "if",
        "for",
        "while",
        "switch",
        "return",
        "case",
        "sizeof",
        "do",
        "else",
        "break",
        "continue",
        "goto",
        "struct",
        "union",
        "enum",
        "typedef",
        "int",
        "char",
        "void",
        "double",
        "float",
        "long",
        "short",
        "unsigned",
        "signed",
        "const",
        "volatile",
        "static",
        "extern",
        "inline",
        "register",
        "NULL",
        "TRUE",
        "FALSE",
        "NG_IGNORE",
        "assert",
        "memcpy",
        "memset",
        "malloc",
        "free",
        "calloc",
        "realloc",
        "printf",
        "fprintf",
        "sprintf",
        "snprintf",
        "exit",
        "abort",
        "isspace",
        "tolower",
        "toupper",
        "strcmp",
        "strncmp",
        "strcpy",
        "strncpy",
        "strlen",
        "strchr",
        "strstr",
        "atoi",
        "atol",
        "atof",
        "fabs",
        "sqrt",
        "exp",
        "log",
        "sin",
        "cos",
        "tan",
        "pow",
        "floor",
        "ceil",
        "main",
    }
)


def expand_call_graph_for_all_records(records: list[dict[str, Any]], repo: Path) -> None:
    """
    Ensure every record has a non-empty call_graph_outgoing:
    merge curated edges with #include targets, resolved intra-repo callees, and netlist anchors.
    """
    sym_index: dict[str, str] = {}
    for f in records:
        for k in f.get("key_functions_defined") or []:
            nm = k.get("name")
            if nm and nm not in sym_index:
                sym_index[nm] = f["path"]

    indexed_paths = {f["path"] for f in records}

    for f in records:
        path = f["path"]
        existing = list(f.get("call_graph_outgoing") or [])
        keys: set[tuple[str | None, str | None]] = {
            (e.get("target_file"), e.get("target_symbol")) for e in existing
        }
        kf = f.get("key_functions_defined") or []
        sym_guess = Path(path).stem
        if kf and isinstance(kf[0], dict) and kf[0].get("name"):
            sym_guess = kf[0]["name"]

        def add_edge(tf: str, ts: str, indirect: bool) -> None:
            key = (tf, ts)
            if key in keys:
                return
            keys.add(key)
            existing.append(
                {
                    "symbol": sym_guess,
                    "target_file": tf,
                    "target_symbol": ts,
                    "indirect": indirect,
                }
            )

        for inc in (f.get("c_includes_internal") or [])[:40]:
            add_edge(inc, "(header_include)", True)

        lang = f.get("language")
        if lang == "c" and path.endswith(".c"):
            fp = repo / path
            if fp.is_file():
                text = fp.read_text(encoding="utf-8", errors="replace")
                added_sym = 0
                for m in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_]{2,})\s*\(", text):
                    callee = m.group(1)
                    if callee in CALLEE_SCAN_SKIP:
                        continue
                    tp = sym_index.get(callee)
                    if tp and tp != path and tp in indexed_paths:
                        add_edge(tp, callee, False)
                        added_sym += 1
                        if added_sym >= 55:
                            break

        if lang == "netlist":
            add_edge("src/frontend/inp.c", "netlist_parse_pipeline", True)
            add_edge("src/spicelib/analysis/dcop.c", "analysis_execution_reference", True)

        if not existing:
            add_edge(path, "(file_anchor)", True)

        f["call_graph_outgoing"] = existing[:120]


def main() -> int:
    repo = REPO_ROOT
    if len(sys.argv) > 1:
        repo = Path(sys.argv[1]).resolve()

    all_files = list(repo.rglob("*"))
    scanned = sum(1 for p in all_files if p.is_file())
    candidates = collect_candidate_files(repo)
    records: list[dict[str, Any]] = []
    skipped = 0
    for sub in [
        "src/maths/ni",
        "src/maths/sparse",
        "src/spicelib/analysis",
        "src/spicelib/devices",
        "src/frontend",
        "src/include/ngspice",
        "tests",
    ]:
        print(f"[PASS1] scanning {sub}/ …")

    for p in candidates:
        rec = build_file_record(p, repo)
        if rec is None:
            skipped += 1
            continue
        records.append(rec)

    chains = canonical_chains_def()
    # verify chain members exist (warn)
    idx = {r["path"] for r in records}
    for c in chains:
        for m in c["canonical_members"]:
            if m not in idx and "<" not in m:
                print(f"[WARN] chain member not indexed: {m}", file=sys.stderr)

    pass2_imported_by(records, repo)
    expand_call_graph_for_all_records(records, repo)
    attach_chain_tags(records, chains)

    st = compute_stats(records, scanned, scanned - len(candidates) + skipped)
    st["total_canonical_chains"] = len(chains)

    output = {
        "repo_name": "ngspice",
        "rag_purpose": "Dual-mission: (1) NodalAI kernel reimplementation oracle; (2) Agentic circuit design and validation platform",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "index_schema_version": "1.0",
        "index_kind": "source_code_dual_mission",
        "primary_languages": ["c", "header", "netlist"],
        "build_systems": ["autoconf"],
        "frameworks_libraries": [
            {
                "name": "ngspice-native sparse",
                "role": "default sparse solver (src/maths/sparse)",
                "vendored": True,
            },
            {"name": "KLU", "role": "optional faster sparse solver", "vendored": False},
            {
                "name": "XSPICE",
                "role": "event-driven mixed-signal extension (src/xspice)",
                "vendored": True,
            },
        ],
        "ngspice_version": "26",
        "domain_summary": (
            "ngspice is an open-source SPICE simulator derived from Berkeley SPICE 3F5, "
            "implementing Modified Nodal Analysis (MNA) with a per-iteration Newton-Raphson loop. "
            "Device models follow the SPICEdev plugin contract (devdefs.h): each device registers "
            "a function-pointer table (DEVload, DEVacLoad, DEVtrunc, DEVlimit, etc.) dispatched "
            "from CKTload. Analysis types include DC operating point, DC sweep, AC small-signal, "
            "transient, noise, distortion (Volterra), sensitivity, pole-zero, and transfer function. "
            "Convergence aids include GMIN stepping, source stepping, and pseudo-transient. "
            "The sparse matrix solver (src/maths/sparse) uses partial-pivoting LU factorization. "
            "The nutmeg/Spice3 frontend parses netlists, expands subcircuits, evaluates parameters, "
            "and supports .control scripting; results are written as binary/ASCII .raw files."
        ),
        "missions": missions_def(),
        "canonical_chains": chains,
        "glossary": glossary_def(),
        "stats": st,
        "groups": build_groups(records, repo),
        "files": records,
    }

    out_path = repo / "rag_index.json"
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(
        f"[OUT] {out_path} — {len(records)} files, "
        f"{len(output['groups'])} groups, {len(chains)} chains"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
