"""
Run .tran decks through the ngspice **batch** binary and parse the binary rawfile.

The HTTP bridge uses **ZMQ** ``ngspice-server`` for transient first (see
``ngspice_client.simulate_transient``). This module is the **fallback**: it shells out to
``ngspice -b`` when ``NGSPICE_CLI`` or ``PATH`` provides a batch binary and ZMQ transient
is unavailable.

Strip interactive ``.control`` / ``plot`` blocks and append ``run`` + ``write … all``.
"""

from __future__ import annotations

import os
import re
import shutil
import struct
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def find_ngspice_cli() -> Optional[str]:
    env = (os.environ.get("NGSPICE_CLI") or "").strip()
    if env and Path(env).is_file():
        return env
    w = shutil.which("ngspice")
    return w if w else None


def strip_control_blocks(netlist: str) -> str:
    """Remove ``.control`` … ``.endc`` (interactive ``plot`` etc. are not batch-safe)."""
    return re.sub(r"(?is)^\.control\s+.*?^\.endc\s*\n?", "", netlist, flags=re.MULTILINE)


def ensure_trailing_end(text: str) -> str:
    t = text.rstrip()
    if not re.search(r"(?im)^\.end\s*$", t):
        t += "\n.end\n"
    return t + ("\n" if not t.endswith("\n") else "")


def build_tran_deck(netlist: str, raw_name: str = "tran_out.raw") -> str:
    core = strip_control_blocks(netlist)
    core = ensure_trailing_end(core)
    inj = (
        f".control\n"
        f"run\n"
        f"write {raw_name} all\n"
        f".endc\n"
    )
    return core.rstrip() + "\n" + inj


def parse_variable_names(header: str) -> List[str]:
    names: List[str] = []
    lines = header.splitlines()
    i = 0
    while i < len(lines):
        if lines[i].strip() == "Variables:" or lines[i].startswith("Variables:"):
            i += 1
            while i < len(lines):
                ln = lines[i]
                s = ln.strip()
                if not s:
                    i += 1
                    continue
                if s.startswith("Binary:") or s.startswith("Values:"):
                    break
                if s.startswith("No. of Data"):
                    i += 1
                    continue
                if s.startswith("No. ") and "Variables" not in s and "Points" not in s:
                    i += 1
                    continue
                parts = [p for p in ln.replace("\t", " ").split(" ") if p]
                if len(parts) >= 2 and parts[0].isdigit():
                    names.append(parts[1])
                i += 1
            break
        i += 1
    return names


def parse_ngspice_binary_raw(raw_path: Path) -> Tuple[List[float], Dict[str, List[float]]]:
    data = raw_path.read_bytes()
    sep = b"Binary:\n"
    pos = data.find(sep)
    if pos < 0:
        sep = b"Binary:\r\n"
        pos = data.find(sep)
    if pos < 0:
        raise ValueError("raw file has no Binary: section (not an ngspice rawfile?)")
    header = data[:pos].decode("utf-8", errors="replace")
    body = data[pos + len(sep) :]
    m_nv = re.search(r"No\. Variables:\s*(\d+)", header)
    m_np = re.search(r"No\. Points:\s*(\d+)", header)
    if not m_nv or not m_np:
        raise ValueError("raw header missing No. Variables / No. Points")
    nv = int(m_nv.group(1))
    npts = int(m_np.group(1))
    names = parse_variable_names(header)
    if len(names) != nv:
        names = [f"var{i}" for i in range(nv)]
    nbytes = nv * npts * 8
    if len(body) < nbytes:
        raise ValueError(f"raw body too short: need {nbytes} bytes, got {len(body)}")
    fmt = "=" + "d" * (nv * npts)
    flat = struct.unpack(fmt, body[:nbytes])
    # ngspice stores points as rows: index (var0, var1, …) per point
    rows: List[List[float]] = []
    for r in range(npts):
        rows.append([flat[r * nv + c] for c in range(nv)])
    cols = list(zip(*rows)) if rows else []
    vectors: Dict[str, List[float]] = {}
    for ci, name in enumerate(names):
        vectors[name.lower()] = list(cols[ci]) if ci < len(cols) else []
    time_key = "time" if "time" in vectors else names[0].lower()
    tvec = vectors.get(time_key, list(range(npts)))
    others = {k: v for k, v in vectors.items() if k != time_key}
    return list(tvec), others


def run_transient(
    netlist: str,
    *,
    timeout_sec: float = 120.0,
) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """
    Returns ``(ok, transient_payload, message)``.
    ``transient_payload`` matches NodalAI / DSO: ``{time, vectors, actual_steps, …}``.
    """
    cli = find_ngspice_cli()
    if not cli:
        return (
            False,
            None,
            "No ngspice batch binary found. Install ngspice and set NGSPICE_CLI, "
            "or ensure `ngspice` is on PATH. (Used only if ZMQ transient already failed.)",
        )
    raw_name = "tran_out.raw"
    deck = build_tran_deck(netlist, raw_name=raw_name)
    t0 = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="vb-tran-") as td:
        tdir = Path(td)
        deck_path = tdir / "deck.cir"
        deck_path.write_text(deck, encoding="utf-8")
        env = os.environ.copy()
        if not env.get("SPICE_LIB_DIR"):
            ng = Path(__file__).resolve().parent.parent / "install" / "share" / "ngspice"
            if ng.is_dir():
                env["SPICE_LIB_DIR"] = str(ng)
        try:
            proc = subprocess.run(
                [cli, "-b", str(deck_path)],
                cwd=str(tdir),
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
            )
        except subprocess.TimeoutExpired:
            return False, None, "ngspice transient run timed out"
        raw_path = tdir / raw_name
        if proc.returncode != 0 or not raw_path.is_file():
            tail = (proc.stderr or proc.stdout or "")[-4000:]
            return False, None, f"ngspice exited {proc.returncode}: {tail}"
        try:
            tvec, vecs = parse_ngspice_binary_raw(raw_path)
        except (ValueError, struct.error, OSError) as e:
            tail = (proc.stderr or proc.stdout or "")[-2000:]
            return False, None, f"failed to parse raw file: {e}. Log tail: {tail}"
    wall_ms = (time.perf_counter() - t0) * 1000.0
    payload: Dict[str, Any] = {
        "time": tvec,
        "vectors": vecs,
        "actual_steps": len(tvec),
        "rejected_steps": 0,
        "h_min_used": 0.0,
        "h_max_used": 0.0,
        "fourier": None,
        "zvs_events": [],
        "sic_desat_events": [],
        "emi_summary": None,
        "soa_events": [],
        "_wall_ms": wall_ms,
    }
    return True, payload, ""
