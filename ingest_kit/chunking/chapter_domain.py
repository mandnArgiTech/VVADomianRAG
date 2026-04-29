"""Ngspice-style chapter filename parsing for domain markdown."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict


def _chapter_meta_from_filename(filename: str) -> Dict[str, str]:
    """Parse ``Chapter_NNN_Title`` stem for chapter number and coarse device family."""
    stem = Path(filename).stem
    m = re.match(r"Chapter_(\d+)_(.*)", stem)
    if not m:
        return {}
    chapter_num = m.group(1)
    rest = m.group(2)
    family_map = (
        ("BJT", "BJT"),
        ("Diode", "DIO"),
        ("Resistor", "RES"),
        ("Capacitor", "CAP"),
        ("Inductor", "IND"),
        ("MOS1", "MOS1"),
        ("MOS2", "MOS2"),
        ("MOS3", "MOS3"),
        ("MOS6", "MOS6"),
        ("MOS9", "MOS9"),
        ("BSIM1", "BSIM1"),
        ("BSIM2", "BSIM2"),
        ("BSIM3", "BSIM3"),
        ("BSIM4v5", "BSIM4V5"),
        ("BSIM4v6", "BSIM4V6"),
        ("BSIM4v7", "BSIM4V7"),
        ("BSIM4", "BSIM4"),
        ("VBIC", "VBIC"),
        ("HFET", "HFET"),
        ("MESFET", "MESFET"),
        ("JFET", "JFET"),
        ("LTRA", "LTRA"),
        ("CIDER", "CIDER"),
        ("XSPICE", "XSPICE"),
        ("Switch", "SW"),
        ("CSW", "CSW"),
        ("CPL", "CPL"),
        ("URC", "URC"),
        ("Tra", "TRA"),
        ("Txl", "TXL"),
        ("ISRC", "ISRC"),
        ("VSRC", "VSRC"),
        ("Dependent", "DEP"),
        ("Mutual", "IND"),
        ("Newton", "CORE"),
        ("NI", "CORE"),
        ("Sparse", "CORE"),
        ("Device", "CORE"),
        ("Simulation", "CORE"),
        ("Core", "CORE"),
        ("Complex", "CORE"),
        ("Derivative", "CORE"),
        ("Polynomial", "CORE"),
        ("Fast", "CORE"),
        ("Floating", "CORE"),
        ("Statistical", "CORE"),
        ("Lexical", "CORE"),
        ("Parse", "CORE"),
        ("Symbol", "CORE"),
        ("Model", "CORE"),
        ("Event", "CORE"),
        ("Analog", "CORE"),
        ("Options", "CORE"),
        ("Memory", "CORE"),
    )
    family = "CORE"
    for prefix, fam in family_map:
        if rest.startswith(prefix):
            family = fam
            break
    return {"chapter_number": chapter_num, "device_family": family}


def _domain_doc_content_type(stem_rest: str, device_family: str) -> str:
    """Classify ngspice domain chapter: algorithm vs device_model vs parser."""
    r = stem_rest
    if any(
        p in r
        for p in (
            "Lexical",
            "Parse",
            "Symbol",
            "INP",
            "Netlist",
            "Preprocessor",
            "XSPICE_Code",
        )
    ):
        return "parser"
    if device_family != "CORE":
        return "device_model"
    if any(
        p in r
        for p in (
            "Newton",
            "NI",
            "Sparse",
            "Integration",
            "Jacobian",
            "Convergence",
            "Truncation",
            "Gear",
            "BDF",
            "LTE",
        )
    ):
        return "algorithm"
    return "algorithm"
