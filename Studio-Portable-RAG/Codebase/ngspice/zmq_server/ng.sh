#!/usr/bin/env bash
# ng.sh — service-style launcher for ngspice-server + bridge + Vite (config: ng.yaml).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

# Prefer a single stack venv under zmq_server/ over an activated subproject venv
# (e.g. vidhubijakam-demo/.venv often has uvicorn but not pyzmq).
PYTHON="python3"
if [ -n "${NG_SH_PYTHON:-}" ] && [ -x "${NG_SH_PYTHON}" ]; then
  PYTHON="${NG_SH_PYTHON}"
elif [ -x "${ROOT}/.venv/bin/python3" ]; then
  PYTHON="${ROOT}/.venv/bin/python3"
elif [ -n "${VIRTUAL_ENV:-}" ] && [ -x "${VIRTUAL_ENV}/bin/python3" ]; then
  PYTHON="${VIRTUAL_ENV}/bin/python3"
fi

SUB="${1:-help}"
shift || true

exec "$PYTHON" - "$ROOT" "$SUB" "$@" <<'PY'
"""Embedded launcher (read by ng.sh via stdin — keep ng.sh as the single committed script)."""
from __future__ import annotations

import json
import os
import re
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import yaml
except ImportError as e:  # pragma: no cover
    print(
        "ng.sh: PyYAML is required for all commands except plain help text.\n"
        "  pip install -r vidhubijakam-demo/requirements-bridge.txt",
        file=sys.stderr,
    )
    raise SystemExit(1) from e


def say(msg: str, end: str = "\n") -> None:
    print(f"ng.sh  {msg}", end=end, flush=True)


def _zmq_client_connect_host(zs: dict) -> str:
    """Host for bridge / clients to connect to REP and PUB (never ``0.0.0.0``)."""
    bind = str(zs.get("bind_addr", "127.0.0.1")).strip()
    explicit = str(zs.get("rep_connect_host", "") or "").strip()
    if explicit:
        return explicit
    if bind in ("0.0.0.0", "*"):
        return "127.0.0.1"
    return bind if bind else "127.0.0.1"


def _zmq_rep_connect_url(zs: dict, rep_port: int) -> str:
    """URL for ``NGSPICE_ZMQ_REP``."""
    h = _zmq_client_connect_host(zs)
    return f"tcp://{h}:{rep_port}"


def _zmq_pub_connect_url(zs: dict, pub_port: int) -> str:
    """URL for ``NGSPICE_ZMQ_PUB`` (diagnostic ``DiagEvent`` stream)."""
    h = _zmq_client_connect_host(zs)
    return f"tcp://{h}:{pub_port}"


def _port_probe_host(socket_bind_host: str) -> str:
    """Host for ``socket.create_connection`` checks when the service binds all interfaces."""
    b = (socket_bind_host or "").strip()
    if b in ("0.0.0.0", "*", ""):
        return "127.0.0.1"
    if b in ("::", "[::]", "::0"):
        return "::1"
    return b if b else "127.0.0.1"


def _tail_log(path: Path, n: int = 45) -> None:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        if not lines:
            say(f"log {path.name} is empty")
            return
        say(f"last {min(n, len(lines))} lines of {path}:")
        for ln in lines[-n:]:
            print(f"ng.sh  | {ln}", flush=True)
    except OSError as e:
        say(f"(could not read log: {e})")


def parse_trailing_args(root: Path, argv: List[str]) -> Tuple[Optional[Path], bool, bool]:
    """Return (config_path or None for default, systemd_system, install_no_start)."""
    cfg: Optional[Path] = None
    system_unit = False
    install_no_start = False
    for a in argv:
        if a in ("--system",):
            system_unit = True
            continue
        if a in ("--no-start",):
            install_no_start = True
            continue
        if a.startswith("-"):
            continue
        p = Path(a)
        if not p.is_absolute():
            p = (Path.cwd() / p).resolve()
            if not p.is_file():
                alt = (root / Path(a)).resolve()
                if alt.is_file():
                    p = alt
        if p.is_file():
            cfg = p
    return cfg, system_unit, install_no_start


def print_help(root: Path) -> None:
    d = root.resolve()
    print(
        f"""ng.sh — manage ngspice ZMQ stack (server + HTTP bridge + Vite)

Usage:
  {d}/ng.sh help
  {d}/ng.sh up   [path/to/ng.yaml]
  {d}/ng.sh down [path/to/ng.yaml]
  {d}/ng.sh restart [path/to/ng.yaml]
  {d}/ng.sh status [path/to/ng.yaml]
  {d}/ng.sh probe  [path/to/ng.yaml]
  {d}/ng.sh install   [path/to/ng.yaml] [--system] [--no-start]
  {d}/ng.sh uninstall [path/to/ng.yaml] [--system]
  {d}/ng.sh remove    [path/to/ng.yaml] [--system]   (alias for uninstall)

install writes a systemd unit, reloads the daemon, then runs enable --now
(systemctl --user for user installs). Pass --no-start to only write the unit
file and skip starting the stack.

Default config: {d}/ng.yaml

Python: ng.sh prefers (1) $NG_SH_PYTHON, (2) {d}/.venv/bin/python3,
  (3) $VIRTUAL_ENV/bin/python3, (4) python3 on PATH.

Requires: Python 3 + PyYAML + pyzmq (+ bridge deps for probe/up bridge).
"""
    )


def _resolve(root: Path, p: str) -> Path:
    x = Path(p)
    return x if x.is_absolute() else (root / x).resolve()


def _load_cfg(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    if not isinstance(raw, dict):
        raise ValueError("ng.yaml root must be a mapping")
    return raw


def _state_paths(root: Path, rt: dict) -> tuple[Path, Path]:
    sd = _resolve(root, rt.get("state_dir", ".ng"))
    ld = _resolve(root, rt.get("log_dir", ".ng/logs"))
    sd.mkdir(parents=True, exist_ok=True)
    ld.mkdir(parents=True, exist_ok=True)
    return sd, ld


def _write_pid(sd: Path, name: str, pid: int) -> None:
    (sd / f"{name}.pid").write_text(str(pid), encoding="utf-8")


def _read_pid(sd: Path, name: str) -> Optional[int]:
    p = sd / f"{name}.pid"
    if not p.is_file():
        return None
    try:
        return int(p.read_text(encoding="utf-8").strip())
    except ValueError:
        return None


def _clear_pid(sd: Path, name: str) -> None:
    p = sd / f"{name}.pid"
    if p.is_file():
        p.unlink()


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _pid_listening_tcp(port: int, host: str = "127.0.0.1") -> Optional[int]:
    """Best-effort: PID of a process listening on TCP ``port`` (Linux ``ss``)."""
    try:
        r = subprocess.run(
            ["ss", "-tlnp"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if r.returncode != 0 or not r.stdout:
            return None
        for line in r.stdout.splitlines():
            line = line.strip()
            if not line.startswith("LISTEN"):
                continue
            parts = line.split(None, 5)
            if len(parts) < 5:
                continue
            local = parts[3]
            if not (local.endswith(f":{port}") or local.endswith(f"]:{port}")):
                continue
            if host in ("127.0.0.1", "localhost"):
                if not (local.startswith("127.0.0.1:") or local.startswith("[::1]:")):
                    continue
            elif host not in ("0.0.0.0", "*", "::", "[::]"):
                if not (local.startswith(f"{host}:") or local.startswith(f"[{host}]:")):
                    continue
            m = re.search(r"pid=(\d+)", line)
            if m:
                return int(m.group(1))
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError, ValueError):
        pass
    return None


def _wait_port(host: str, port: int, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return True
        except OSError:
            time.sleep(0.15)
    return False


def _port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.35):
            return True
    except OSError:
        return False


def _wait_port_closed(host: str, port: int, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _port_open(host, port):
            return True
        time.sleep(0.12)
    return False


def _wait_pid_exit(pid: int, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _pid_alive(pid):
            return True
        time.sleep(0.1)
    return False


def _kill_pid(pid: int, sig: int = signal.SIGTERM) -> None:
    try:
        os.kill(pid, sig)
    except ProcessLookupError:
        pass


def _signal_process_group(pid: int, sig: int) -> None:
    """Signal the whole session/process group (Vite/npx trees). Falls back to single PID."""
    try:
        os.killpg(os.getpgid(pid), sig)
    except (ProcessLookupError, PermissionError, OSError):
        _kill_pid(pid, sig)


def _run_capture(cmd: List[str], *, cwd: Optional[Path] = None, env: Optional[dict] = None) -> str:
    r = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return (r.stdout or "") + (r.stderr or "")


def _zmq_server_version(binary: Path) -> str:
    try:
        out = _run_capture([str(binary), "--version"]).strip()
        if out:
            return out.splitlines()[0].strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return "unknown"


def _ldd_map(binary: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    try:
        txt = _run_capture(["ldd", str(binary)])
        for line in txt.splitlines():
            m = re.match(r"^\s*(\S+)\s*=>\s+(\S+)", line)
            if m:
                out[m.group(1)] = m.group(2)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return out


def _ngspice_lib_file(root: Path, zs: dict) -> Optional[Path]:
    share = _resolve(root, zs["spice_lib_dir"])
    cand = share.parent.parent / "lib" / "libngspice.so.0"
    if cand.is_file():
        return cand
    return None


def _strings_ngspice_version(lib: Path) -> Optional[str]:
    try:
        txt = _run_capture(["strings", str(lib)])
        for pat in (r"ngspice-\d+\.\d+", r"\b\d+\.\d+\.\d+\s+ngspice\b", r"\bngspice\s+\d+\.\d+\.\d+\b"):
            m = re.search(pat, txt, re.I)
            if m:
                return m.group(0)
        m = re.search(r"\b\d+\.\d+\.\d+\b", txt)
        if m and m.group(0) not in ("1.0.0", "0.0.0"):
            return m.group(0)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return None


def _py_mod_versions() -> Tuple[Optional[str], Optional[str], Optional[str]]:
    zmq_v = pyzmq_v = uv_v = None
    try:
        import zmq as _z

        zmq_v = _z.zmq_version()
        pyzmq_v = _z.__version__
    except Exception:
        pass
    try:
        import uvicorn as _u

        uv_v = _u.__version__
    except Exception:
        pass
    return zmq_v, pyzmq_v, uv_v


def _vite_cli_version(fe_dir: Path) -> str:
    try:
        out = _run_capture(["npx", "vite", "--version"], cwd=fe_dir).strip()
        return out.splitlines()[-1].strip() if out else "unknown"
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return "unknown"


def _fmt_uptime(seconds: float) -> str:
    if seconds < 0 or seconds > 86400 * 365 * 10:
        return "—"
    s = int(seconds)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _shutdown_one(
    label: str,
    host: str,
    port: int,
    pid: Optional[int],
    sd: Path,
    name: str,
    timeout: float,
    *,
    port_wait: Optional[float] = None,
) -> None:
    pwait = port_wait if port_wait is not None else min(8.0, max(2.0, timeout))
    if pid is None or not _pid_alive(pid):
        say(f"stopping {label:10} (no live pid) … already down")
        _clear_pid(sd, name)
        _wait_port_closed(host, port, min(2.0, pwait))
        return
    t0 = time.monotonic()
    _signal_process_group(pid, signal.SIGTERM)
    exited = _wait_pid_exit(pid, timeout)
    forced = ""
    if not exited:
        forced = "SIGKILL after timeout; "
        _signal_process_group(pid, signal.SIGKILL)
        _wait_pid_exit(pid, 2.0)
    _clear_pid(sd, name)
    closed = _wait_port_closed(host, port, pwait)
    dt = time.monotonic() - t0
    extra = "port released" if closed else "port still in use (check logs)"
    say(
        f"stopping {label:10} (pid {pid}) … {forced}"
        f"done in {dt:.1f}s ({extra})"
    )


def cmd_down(root: Path, cfg: dict, cfg_path: Path) -> int:
    rt = cfg.get("runtime", {})
    sv = cfg.get("service", {})
    sd, _ld = _state_paths(root, rt)
    timeout = float(sv.get("shutdown_timeout_sec", 10))
    zs = cfg["zmq_server"]
    br = cfg["bridge"]
    fe = cfg["frontend"]
    bind = str(zs.get("bind_addr", "127.0.0.1"))
    rep, pub = int(zs["rep_port"]), int(zs["pub_port"])
    bh, bp = str(br.get("host", "127.0.0.1")), int(br["port"])
    fh, fp = str(fe.get("host", "127.0.0.1")), int(fe["port"])
    zmq_probe = _port_probe_host(bind)
    b_probe = _port_probe_host(bh)
    f_probe = _port_probe_host(fh)

    say(f"down  config: {cfg_path}")
    _shutdown_one(
        "vite", f_probe, fp, _read_pid(sd, "vite"), sd, "vite", timeout, port_wait=max(timeout, 15.0)
    )
    _shutdown_one("bridge", b_probe, bp, _read_pid(sd, "bridge"), sd, "bridge", timeout)
    _shutdown_one("zmq-srv", zmq_probe, rep, _read_pid(sd, "zmq_server"), sd, "zmq_server", timeout)
    if not _port_open(zmq_probe, pub):
        say(f"down  PUB {bind}:{pub} closed (checked via {zmq_probe})")
    else:
        say(f"down  PUB {bind}:{pub} still open (checked via {zmq_probe}; see logs)")
    say("down  complete.")
    return 0


def cmd_up(root: Path, cfg: dict, cfg_path: Path) -> int:
    zs = cfg["zmq_server"]
    br = cfg["bridge"]
    fe = cfg["frontend"]
    rt = cfg.get("runtime", {})
    sv = cfg.get("service", {})

    t_stack = time.monotonic()
    sd, ld = _state_paths(root, rt)
    bind = str(zs.get("bind_addr", "127.0.0.1"))
    rep, pub = int(zs["rep_port"]), int(zs["pub_port"])
    rep_url = _zmq_rep_connect_url(zs, rep)
    pub_url = _zmq_pub_connect_url(zs, pub)
    zmq_probe = _port_probe_host(bind)

    say(f"config file : {cfg_path.resolve()}")
    say("effective YAML (merged keys):")
    for line in yaml.safe_dump(cfg, default_flow_style=False, sort_keys=False).splitlines():
        print(f"    {line}", flush=True)

    if _port_open(zmq_probe, rep):
        say(f"error: REP port {rep} already in use (checked {zmq_probe}). Run: ./ng.sh down")
        return 1

    for name in ("vite", "bridge", "zmq_server"):
        _clear_pid(sd, name)

    if rt.get("pip_install_bridge"):
        req = _resolve(root, rt.get("bridge_requirements", "vidhubijakam-demo/requirements-bridge.txt"))
        say(f"pip install -r {req} (runtime.pip_install_bridge=true)")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(req)], check=False)

    spice = _resolve(root, zs["spice_lib_dir"])
    if not spice.is_dir():
        say(f"error: spice_lib_dir is not a directory: {spice}")
        return 1

    binary = _resolve(root, zs["binary"])
    if not binary.is_file():
        say(f"error: ngspice-server binary missing: {binary}")
        say('  Build with: make -C "' + str(root) + '"')
        return 1

    nglib = _ngspice_lib_file(root, zs)
    ldd = _ldd_map(binary)
    ngspice_line = _strings_ngspice_version(nglib) if nglib else None
    zver = _zmq_server_version(binary)
    say(
        f"stack meta  : service={sv.get('name', 'ngspice-stack')}  "
        f"yaml_version={sv.get('version', '')}  SPICE_LIB_DIR={spice}"
    )
    say(
        "ngspice     : "
        + (ngspice_line or "version n/a (strings)")
        + (f"  [{nglib}]" if nglib else "")
    )
    say("zmq-server  : " + zver + f"  binary={binary}")
    say("linked libs : " + ", ".join(f"{k} → {v}" for k, v in sorted(ldd.items())))

    say(f"python exe  : {sys.executable}")
    zmq_v, pyzmq_v, uv_v = _py_mod_versions()
    say(
        "python zmq  : "
        + (f"libzmq {zmq_v}  pyzmq {pyzmq_v}" if zmq_v else "zmq not importable")
        + (f"  uvicorn {uv_v}" if uv_v else "")
    )
    if zmq_v is None:
        say("error: pyzmq is required for the HTTP bridge and ng.sh probe.")
        say("  pip install pyzmq")
        say("  pip install -r vidhubijakam-demo/requirements-bridge.txt")
        say("  Or create zmq_server/.venv with those deps; ng.sh prefers it over $VIRTUAL_ENV.")
        say("  Or export NG_SH_PYTHON=/path/to/python3 that has pyzmq.")
        return 1

    zlog = open(ld / "zmq_server.log", "w", encoding="utf-8")
    zenv = os.environ.copy()
    zenv["SPICE_LIB_DIR"] = str(spice)
    zargs = [
        str(binary),
        "--bind-addr",
        bind,
        "--rep-port",
        str(rep),
        "--pub-port",
        str(pub),
    ]
    zp = subprocess.Popen(
        zargs,
        cwd=str(root),
        env=zenv,
        stdout=zlog,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    _write_pid(sd, "zmq_server", zp.pid)
    if not _wait_port(zmq_probe, rep, float(zs.get("startup_timeout_sec", 30))):
        say(f"error: zmq_server did not open REP port. See {ld / 'zmq_server.log'}")
        _kill_pid(zp.pid, signal.SIGKILL)
        _clear_pid(sd, "zmq_server")
        return 1
    say(
        "zmq-srv     : UP  LISTEN tcp://"
        + f"{bind}:{rep}  PUB tcp://{bind}:{pub}  bridge REP {rep_url}  diag PUB {pub_url}"
    )

    br_dir = _resolve(root, br["working_directory"])
    py_path = _resolve(root, br["pythonpath"])
    bhost = str(br.get("host", "127.0.0.1"))
    bport = int(br["port"])
    b_probe = _port_probe_host(bhost)
    benv = os.environ.copy()
    benv["PYTHONPATH"] = str(py_path)
    benv["NGSPICE_ZMQ_REP"] = rep_url
    benv["NGSPICE_ZMQ_PUB"] = pub_url
    bmod = str(br.get("module", "bridge_server:app"))

    # Pre-flight: verify all bridge imports succeed BEFORE spawning uvicorn.
    req_mods = {"zmq": "pyzmq", "google.protobuf": "protobuf", "fastapi": "fastapi", "uvicorn": "uvicorn"}
    missing: list[str] = []
    for mod, pkg in req_mods.items():
        code = f"import {mod}"
        r = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, timeout=10,
            env=benv, cwd=str(br_dir),
        )
        if r.returncode != 0:
            missing.append(pkg)
    if missing:
        say(f"error: bridge pre-flight failed — missing packages: {', '.join(missing)}")
        say(f"  pip install {' '.join(missing)}")
        say("  pip install -r vidhubijakam-demo/requirements-bridge.txt")
        say(f"  (Python: {sys.executable})")
        _kill_pid(zp.pid, signal.SIGKILL)
        _clear_pid(sd, "zmq_server")
        return 1

    blog = open(ld / "bridge.log", "w", encoding="utf-8")
    uv_workers = int(br.get("uvicorn_workers", 1) or 1)
    _uw_env = os.environ.get("NGSPICE_UVICORN_WORKERS", "").strip()
    if _uw_env.isdigit():
        uv_workers = int(_uw_env)
    if uv_workers < 1:
        uv_workers = 1
    if uv_workers > 32:
        uv_workers = 32
    uv_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        bmod,
        "--host",
        bhost,
        "--port",
        str(bport),
    ]
    if uv_workers > 1:
        uv_cmd.extend(["--workers", str(uv_workers)])
    bp = subprocess.Popen(
        uv_cmd,
        cwd=str(br_dir),
        env=benv,
        stdout=blog,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    _write_pid(sd, "bridge", bp.pid)
    if not _wait_port(b_probe, bport, float(br.get("startup_timeout_sec", 30))):
        say(f"error: bridge did not open HTTP port. Full log: {ld / 'bridge.log'}")
        _tail_log(ld / "bridge.log")
        _kill_pid(bp.pid, signal.SIGKILL)
        _kill_pid(zp.pid, signal.SIGKILL)
        for n in ("bridge", "zmq_server"):
            _clear_pid(sd, n)
        return 1
    say(f"bridge      : UP  http://{bhost}:{bport}  (PYTHONPATH={py_path})")

    fe_dir = _resolve(root, fe["working_directory"])
    vcfg = _resolve(root, fe["vite_config"])
    fhost = str(fe.get("host", "127.0.0.1"))
    fport = int(fe["port"])
    f_probe = _port_probe_host(fhost)
    vv = _vite_cli_version(fe_dir)
    flog = open(ld / "vite.log", "w", encoding="utf-8")
    fenv = os.environ.copy()
    fenv["ECAD_API_PORT"] = str(bport)
    fenv["VITE_PROXY_API_PORT"] = str(bport)
    fp = subprocess.Popen(
        ["npx", "vite", "--config", str(vcfg), "--host", fhost, "--port", str(fport), "--strictPort"],
        cwd=str(fe_dir),
        env=fenv,
        stdout=flog,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    _write_pid(sd, "vite", fp.pid)
    if not _wait_port(f_probe, fport, float(fe.get("startup_timeout_sec", 45))):
        say(f"error: Vite did not open port. Full log: {ld / 'vite.log'}")
        _tail_log(ld / "vite.log")
        _kill_pid(fp.pid, signal.SIGKILL)
        _kill_pid(bp.pid, signal.SIGKILL)
        _kill_pid(zp.pid, signal.SIGKILL)
        for n in ("vite", "bridge", "zmq_server"):
            _clear_pid(sd, n)
        return 1
    node_pid = _pid_listening_tcp(fport, fhost)
    if node_pid:
        _write_pid(sd, "vite", node_pid)
    say(f"ui (vite)   : UP  {vv}  http://{fhost}:{fport}")

    started_at = time.time()
    meta = {
        "started_at": started_at,
        "config": str(cfg_path.resolve()),
        "service_version_yaml": sv.get("version", ""),
        "rep_url": rep_url,
        "ui": f"http://{fhost}:{fport}",
        "bridge": f"http://{bhost}:{bport}",
        "logs": str(ld),
        "pids": {k: _read_pid(sd, k) for k in ("zmq_server", "bridge", "vite")},
    }
    (sd / "last_up.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    elapsed = time.monotonic() - t_stack
    say(f"✓ stack up in {elapsed:.1f}s — logs: {ld}")
    return 0


def cmd_status(root: Path, cfg: dict, cfg_path: Path) -> int:
    zs = cfg["zmq_server"]
    br = cfg["bridge"]
    fe = cfg["frontend"]
    rt = cfg.get("runtime", {})
    sd, ld = _state_paths(root, rt)
    bind = str(zs.get("bind_addr", "127.0.0.1"))
    rep, pub = int(zs["rep_port"]), int(zs["pub_port"])
    bh, bp = str(br.get("host", "127.0.0.1")), int(br["port"])
    fh, fp = str(fe.get("host", "127.0.0.1")), int(fe["port"])
    zmq_probe = _port_probe_host(bind)
    b_probe = _port_probe_host(bh)
    f_probe = _port_probe_host(fh)
    now = time.time()

    def row(label: str, pid: Optional[int], host: str, ports: List[Tuple[str, int]]) -> str:
        alive = pid is not None and _pid_alive(pid)
        st = "RUNNING" if alive else "DOWN"
        parts = [f"{label:9}", st]
        if pid is not None:
            parts.append(f"pid={pid}")
        for pname, po in ports:
            o = "OPEN" if _port_open(host, po) else "closed"
            parts.append(f"{pname}:{po} {o}")
        lu = None
        try:
            j = json.loads((sd / "last_up.json").read_text(encoding="utf-8"))
            lu = float(j.get("started_at", 0))
        except (OSError, ValueError, json.JSONDecodeError):
            pass
        if alive and lu:
            parts.append(f"uptime={_fmt_uptime(now - lu)}")
        return "  ".join(parts)

    say(f"config   : {cfg_path.resolve()}")
    say(row("zmq-srv", _read_pid(sd, "zmq_server"), zmq_probe, [("REP", rep), ("PUB", pub)]))
    say(row("bridge", _read_pid(sd, "bridge"), b_probe, [("HTTP", bp)]))
    say(row("vite", _read_pid(sd, "vite"), f_probe, [("HTTP", fp)]))
    rep_ok = _port_open(zmq_probe, rep)
    overall = "UP" if rep_ok and _port_open(b_probe, bp) else "DEGRADED" if rep_ok else "DOWN"
    say(f"overall  : {overall}")
    say(f"logs     : {ld}")
    return 0


def cmd_probe(root: Path, cfg: dict, cfg_path: Path) -> int:
    zs = cfg["zmq_server"]
    br = cfg["bridge"]
    py_path = _resolve(root, br["pythonpath"])
    rep = int(zs["rep_port"])
    rep_url = _zmq_rep_connect_url(zs, rep)
    say(f"probe  config: {cfg_path.resolve()}")
    say(f"probe  ZMQ REP {rep_url}")
    netlist = (
        "* ng.sh probe\n"
        "V1 n1 0 DC 1.0\n"
        "R1 n1 0 1k\n"
        ".op\n"
        ".end\n"
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(py_path)
    code = f"""
import sys, time
sys.path.insert(0, {str(py_path)!r})
from ngspice_client import NgspiceClient
t0 = time.perf_counter()
c = NgspiceClient({rep_url!r})
r = c.simulate({netlist!r}, analysis="op", timeout_sec=30.0)
dt = (time.perf_counter() - t0) * 1000.0
print("RT_MS=" + str(round(dt, 3)))
print("CONVERGED=" + str(bool(r.converged)))
print("ERROR=" + str(int(r.error)))
c.close()
"""
    try:
        out = subprocess.run(
            [sys.executable, "-c", code],
            cwd=str(root),
            env=env,
            capture_output=True,
            text=True,
            timeout=45,
            check=False,
        )
        txt = (out.stdout or "") + (out.stderr or "")
        if out.returncode != 0:
            say(f"probe  error (exit {out.returncode}): {txt.strip() or 'no output'}")
            return 1
        rt_ms = conv = err = None
        for line in txt.splitlines():
            if line.startswith("RT_MS="):
                rt_ms = line.split("=", 1)[1].strip()
            elif line.startswith("CONVERGED="):
                conv = line.split("=", 1)[1].strip()
            elif line.startswith("ERROR="):
                err = line.split("=", 1)[1].strip()
        binary = _resolve(root, zs["binary"])
        nglib = _ngspice_lib_file(root, zs)
        ngver = _strings_ngspice_version(nglib) if nglib else "n/a"
        say(
            "probe  "
            + f"round-trip {rt_ms} ms  converged={conv}  error={err}  ngspice_lib≈{ngver}"
        )
        say("probe  zmq-server: " + _zmq_server_version(binary))
        return 0
    except subprocess.TimeoutExpired:
        say("probe  timed out")
        return 1


def _unit_paths(service_name: str, system: bool) -> Tuple[Path, Path]:
    safe = re.sub(r"[^a-zA-Z0-9._-]+", "-", service_name).strip("-") or "ngspice-stack"
    unit = f"{safe}.service"
    if system:
        return Path("/etc/systemd/system") / unit, Path("/etc/systemd/system")
    home = Path.home()
    return home / ".config/systemd/user" / unit, home / ".config/systemd/user"


def cmd_install(root: Path, cfg: dict, cfg_path: Path, system: bool, no_start: bool) -> int:
    sv = cfg.get("service", {})
    name = str(sv.get("name", "ngspice-stack"))
    unit_path, unit_dir = _unit_paths(name, system)
    if system and os.geteuid() != 0:
        say("install  error: --system requires root (sudo).")
        return 1
    unit_dir.mkdir(parents=True, exist_ok=True)
    ng_sh = (root / "ng.sh").resolve()
    cfg_abs = cfg_path.resolve()
    body = f"""[Unit]
Description=ngspice ZMQ stack ({name}, ng.sh)
After=network-online.target
Wants=network-online.target

[Service]
Type=forking
WorkingDirectory={root.resolve()}
PIDFile={(_resolve(root, cfg.get('runtime', {}).get('state_dir', '.ng')) / 'zmq_server.pid').resolve()}
ExecStart={ng_sh} up {cfg_abs}
ExecStop={ng_sh} down {cfg_abs}
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
"""
    unit_path.write_text(body, encoding="utf-8")
    say(f"install  wrote {unit_path}")
    scope = [] if system else ["--user"]
    subprocess.run(["systemctl", *scope, "daemon-reload"], check=False)
    scmd = " ".join(["systemctl", *scope]).strip() or "systemctl"

    if no_start:
        say("install  skipped enable (--no-start). To start later:")
        say(f"  {scmd} enable --now {unit_path.name}")
        return 0

    r = subprocess.run(
        ["systemctl", *scope, "enable", "--now", unit_path.name],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if r.returncode == 0:
        say(f"install  {scmd} enable --now {unit_path.name}  (ok)")
        return 0

    say(f"install  enable --now failed (exit {r.returncode})")
    if (r.stderr or "").strip():
        for line in r.stderr.strip().splitlines():
            say(f"  {line}")
    say("install  run manually:")
    say(f"  {scmd} enable --now {unit_path.name}")
    if not system:
        say("install  user services need a login session; for boot w/o login:")
        say("  sudo loginctl enable-linger $USER")
    return 1


def cmd_uninstall(root: Path, cfg: dict, cfg_path: Path, system: bool) -> int:
    sv = cfg.get("service", {})
    name = str(sv.get("name", "ngspice-stack"))
    unit_path, _ = _unit_paths(name, system)
    if system and os.geteuid() != 0:
        say("uninstall  error: --system requires root (sudo).")
        return 1
    scope = [] if system else ["--user"]
    if unit_path.is_file():
        subprocess.run(["systemctl", *scope, "stop", unit_path.name], check=False)
        subprocess.run(["systemctl", *scope, "disable", unit_path.name], check=False)
        unit_path.unlink(missing_ok=True)
        say(f"uninstall  removed {unit_path}")
    else:
        say(f"uninstall  unit not found: {unit_path}")
    subprocess.run(["systemctl", *scope, "daemon-reload"], check=False)
    cmd_down(root, cfg, cfg_path)
    return 0


def main() -> int:
    if len(sys.argv) < 3:
        print("ng.sh: internal argv error", file=sys.stderr)
        return 2
    root = Path(sys.argv[1]).resolve()
    sub = sys.argv[2]
    rest = sys.argv[3:]

    if sub in ("help", "-h", "--help"):
        print_help(root)
        return 0

    cfg_override, system, install_no_start = parse_trailing_args(root, rest)
    cfg_path = cfg_override if cfg_override is not None else (root / "ng.yaml")
    if not cfg_path.is_file():
        say(f"error: config not found: {cfg_path}")
        return 1
    cfg = _load_cfg(cfg_path)

    if sub == "up":
        return cmd_up(root, cfg, cfg_path)
    if sub == "down":
        return cmd_down(root, cfg, cfg_path)
    if sub == "restart":
        cmd_down(root, cfg, cfg_path)
        return cmd_up(root, cfg, cfg_path)
    if sub == "status":
        return cmd_status(root, cfg, cfg_path)
    if sub == "probe":
        return cmd_probe(root, cfg, cfg_path)
    if sub == "install":
        return cmd_install(root, cfg, cfg_path, system, install_no_start)
    if sub in ("uninstall", "remove"):
        return cmd_uninstall(root, cfg, cfg_path, system)

    print_help(root)
    say(f"error: unknown command {sub!r}")
    return 2


raise SystemExit(main())
PY
