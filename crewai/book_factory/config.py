"""YAML parsing and merged settings (paths, API key, logging)."""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
from typing import Any, NamedTuple

from .constants import DEFAULT_SOURCE_ROOT
from .exceptions import BookFactoryConfigError

# Top-level keys accepted in crewai/config.yaml (and any --config file). Aliases share semantics.
CONFIG_YAML_ALLOWED_KEYS: frozenset[str] = frozenset(
    {
        "source_root",
        "ngspice_root",
        "source_directory",
        "ngspice_directory",
        "output_dir",
        "output_directory",
        "chapter_ledger",
        "ledger",
        "chapter_ledger_json",
        "project_prompts",
        "project_prompts_json",
        "prompts_file",
        "deepseek_api_key",
        "api_key",
        "deepseek_key",
        "log_file",
        "log_path",
        "log_level",
    }
)

_PATH_KEYS = frozenset(
    {
        "source_root",
        "ngspice_root",
        "source_directory",
        "ngspice_directory",
        "output_dir",
        "output_directory",
        "chapter_ledger",
        "ledger",
        "chapter_ledger_json",
        "project_prompts",
        "project_prompts_json",
        "prompts_file",
        "log_file",
        "log_path",
    }
)

_API_KEY_KEYS = frozenset({"deepseek_api_key", "api_key", "deepseek_key"})


def _reject_bool(label: str, value: Any, path: Path) -> None:
    if isinstance(value, bool):
        raise BookFactoryConfigError(
            f"{path}: key {label!r} must not be a YAML boolean; use a string or number for paths, "
            "or a string for log_level / API key."
        )


def _expect_path_scalar(label: str, value: Any, path: Path) -> None:
    if value is None:
        return
    _reject_bool(label, value, path)
    if isinstance(value, Path):
        return
    if isinstance(value, (str, int, float)):
        return
    raise BookFactoryConfigError(
        f"{path}: key {label!r} must be a string, number, or null (got {type(value).__name__})."
    )


def validate_config_yaml_document(data: dict[str, Any], *, path: Path) -> None:
    """Reject unknown keys and invalid value types for a loaded config mapping.

    Call after ``yaml.safe_load`` so users get immediate feedback on typos
    (e.g. ``souce_root``) and wrong types (e.g. nested mappings for ``log_level``).
    """
    unknown = set(data.keys()) - CONFIG_YAML_ALLOWED_KEYS
    if unknown:
        raise BookFactoryConfigError(
            f"{path}: unknown config key(s): {', '.join(sorted(unknown))}. "
            f"Allowed: {', '.join(sorted(CONFIG_YAML_ALLOWED_KEYS))}."
        )

    for key in _PATH_KEYS:
        if key not in data:
            continue
        _expect_path_scalar(key, data[key], path)

    if "log_level" in data and data["log_level"] is not None:
        _reject_bool("log_level", data["log_level"], path)
        lv = data["log_level"]
        if not isinstance(lv, (str, int)):
            raise BookFactoryConfigError(
                f"{path}: log_level must be a string (e.g. INFO) or integer level (got {type(lv).__name__})."
            )

    for key in _API_KEY_KEYS:
        if key not in data or data[key] is None:
            continue
        v = data[key]
        if not isinstance(v, str):
            raise BookFactoryConfigError(
                f"{path}: {key!r} must be a string when set (got {type(v).__name__})."
            )


try:
    import yaml
except ImportError as exc:  # pragma: no cover
    yaml = None  # type: ignore[assignment]
    _YAML_IMPORT_ERROR = exc
else:
    _YAML_IMPORT_ERROR = None


class BookFactorySettings(NamedTuple):
    """Fully resolved settings for one batch run."""

    source_root: Path
    output_dir: Path
    ledger_json: Path
    prompts_json: Path
    api_key: str
    log_file: Path | None
    log_level: int


def yaml_pick(mapping: dict[str, Any], *keys: str) -> Any:
    for k in keys:
        if k not in mapping:
            continue
        v = mapping[k]
        if v is None:
            continue
        if isinstance(v, str) and not v.strip():
            continue
        return v
    return None


def parse_yaml_file(path: Path) -> dict[str, Any]:
    if yaml is None:
        raise BookFactoryConfigError(
            "PyYAML is required for --config. Install with:  pip install PyYAML"
        ) from _YAML_IMPORT_ERROR
    if not path.is_file():
        raise BookFactoryConfigError(f"Config file not found:\n  {path}")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))  # type: ignore[union-attr]
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:  # type: ignore[union-attr]
        raise BookFactoryConfigError(f"Cannot read YAML config {path}: {exc}") from exc
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise BookFactoryConfigError(
            f"YAML root must be a mapping (object), got {type(raw).__name__}."
        )
    validate_config_yaml_document(raw, path=path)
    return raw


def resolve_path_str(base_dir: Path, value: Any) -> Path | None:
    if value is None:
        return None
    if isinstance(value, Path):
        s = str(value)
    elif isinstance(value, (int, float)):
        s = str(int(value) if isinstance(value, float) and value.is_integer() else value)
    else:
        s = str(value).strip()
    if not s:
        return None
    p = Path(s).expanduser()
    if not p.is_absolute():
        p = (base_dir / p).resolve()
    return p.resolve()


def parse_log_level(name: str) -> int:
    n = name.strip().upper()
    if hasattr(logging, "getLevelNamesMapping"):
        mapping = logging.getLevelNamesMapping()
        if n not in mapping:
            allowed = ", ".join(sorted(mapping))
            raise BookFactoryConfigError(f"Invalid log_level {name!r}. Use one of: {allowed}")
        return mapping[n]
    level = logging._nameToLevel.get(n)
    if level is None:
        allowed = ", ".join(sorted(logging._nameToLevel))
        raise BookFactoryConfigError(f"Invalid log_level {name!r}. Use one of: {allowed}")
    return level


def resolve_book_factory_settings(
    *,
    script_dir: Path,
    yaml_path: Path | None,
    yaml_data: dict[str, Any],
    args: argparse.Namespace,
) -> BookFactorySettings:
    """Merge order: defaults < YAML < environment < CLI (same as paths for files)."""
    yaml_base = yaml_path.parent if yaml_path is not None else script_dir

    source: Path | None = None
    out_dir: Path | None = None
    ledger: Path | None = None
    prompts_json: Path | None = None
    api_key: str | None = None
    log_file: Path | None = None
    log_level: int | None = None

    y_src = yaml_pick(
        yaml_data,
        "source_root",
        "ngspice_root",
        "source_directory",
        "ngspice_directory",
    )
    y_out = yaml_pick(yaml_data, "output_dir", "output_directory")
    y_led = yaml_pick(yaml_data, "chapter_ledger", "ledger", "chapter_ledger_json")
    y_pr = yaml_pick(yaml_data, "project_prompts", "project_prompts_json", "prompts_file")
    y_key = yaml_pick(yaml_data, "deepseek_api_key", "api_key", "deepseek_key")
    y_log = yaml_pick(yaml_data, "log_file", "log_path")
    y_lvl = yaml_pick(yaml_data, "log_level")

    if y_src is not None:
        source = resolve_path_str(yaml_base, y_src)
    if y_out is not None:
        out_dir = resolve_path_str(yaml_base, y_out)
    if y_led is not None:
        ledger = resolve_path_str(yaml_base, y_led)
    if y_pr is not None:
        p = resolve_path_str(yaml_base, y_pr)
        if p is not None:
            prompts_json = p
    if y_key is not None:
        api_key = str(y_key).strip() or None
    if y_log is not None:
        lp = resolve_path_str(yaml_base, y_log)
        if lp is not None:
            log_file = lp
    if y_lvl is not None:
        if isinstance(y_lvl, int):
            lv = int(y_lvl)
            if not 0 <= lv <= 50:
                raise BookFactoryConfigError(f"Invalid numeric log_level in YAML: {lv}")
            log_level = lv
        else:
            log_level = parse_log_level(str(y_lvl))

    env_src = os.environ.get("NGSPICE_BOOK_SOURCE_ROOT", "").strip()
    env_out = os.environ.get("NGSPICE_BOOK_OUTPUT_DIR", "").strip()
    env_led = os.environ.get("NGSPICE_BOOK_LEDGER", "").strip()
    env_pr = os.environ.get("NGSPICE_BOOK_PROJECT_PROMPTS", "").strip()
    env_log = os.environ.get("NGSPICE_BOOK_LOG_FILE", "").strip()
    env_lvl = os.environ.get("NGSPICE_BOOK_LOG_LEVEL", "").strip()
    env_key = (
        os.environ.get("DEEPSEEK_API_KEY", "").strip()
        or os.environ.get("OPENAI_API_KEY", "").strip()
        or None
    )

    if env_src:
        source = Path(env_src).expanduser().resolve()
    if env_out:
        out_dir = Path(env_out).expanduser().resolve()
    if env_led:
        ledger = Path(env_led).expanduser().resolve()
    if env_pr:
        prompts_json = Path(env_pr).expanduser().resolve()
    if env_log:
        log_file = Path(env_log).expanduser().resolve()
    if env_lvl:
        log_level = parse_log_level(env_lvl)
    if not api_key and env_key:
        api_key = env_key

    if getattr(args, "source_root", None) is not None:
        source = Path(args.source_root).expanduser().resolve()
    if getattr(args, "output_dir", None) is not None:
        out_dir = Path(args.output_dir).expanduser().resolve()
    if getattr(args, "ledger", None) is not None:
        ledger = Path(args.ledger).expanduser().resolve()
    if getattr(args, "project_prompts", None) is not None:
        prompts_json = Path(args.project_prompts).expanduser().resolve()
    if hasattr(args, "log_file"):
        log_file = Path(args.log_file).expanduser().resolve()
    if hasattr(args, "log_level"):
        log_level = parse_log_level(str(args.log_level))

    if getattr(args, "deepseek_api_key", None) is not None:
        api_key = str(args.deepseek_api_key).strip()

    if source is None:
        source = Path(DEFAULT_SOURCE_ROOT).resolve()
    if out_dir is None:
        out_dir = (script_dir / "output").resolve()
    if ledger is None:
        ledger = (script_dir / "chapter_ledger.json").resolve()
    if prompts_json is None:
        prompts_json = (script_dir / "project_prompts.json").resolve()
    if log_level is None:
        log_level = logging.INFO

    return BookFactorySettings(
        source_root=source,
        output_dir=out_dir,
        ledger_json=ledger,
        prompts_json=prompts_json,
        api_key=api_key or "",
        log_file=log_file,
        log_level=log_level,
    )
