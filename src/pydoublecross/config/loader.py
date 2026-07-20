# SPDX-FileCopyrightText: 2026 James G Willmore
# SPDX-License-Identifier: Apache-2.0

"""Load and save the YAML configuration document."""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

import yaml

from pydoublecross.config.models import AppConfig
from pydoublecross.exceptions import ConfigError

_ENV_REF = re.compile(r"\$\{env:([A-Za-z_]\w*)\}", re.ASCII)


def _interpolate_env_string(raw: str) -> str:
    def replace(match: re.Match[str]) -> str:
        var_name = match.group(1)
        try:
            return os.environ[var_name]
        except KeyError as exc:
            raise ConfigError(
                f"config references environment variable '{var_name}' which is not set"
            ) from exc

    return _ENV_REF.sub(replace, raw)


def _interpolate_env(value: object) -> object:
    """Recursively substitute `${env:VAR}` in string values only (not comments/keys)."""
    if isinstance(value, str):
        return _interpolate_env_string(value)
    if isinstance(value, dict):
        return {key: _interpolate_env(val) for key, val in value.items()}
    if isinstance(value, list):
        return [_interpolate_env(item) for item in value]
    return value


def _resolve_file_paths(config: AppConfig, base_dir: Path) -> None:
    """Resolve relative sqlite/duckdb `path` values against the config file's directory."""
    for ds in config.data_sources.values():
        if ds.type in ("sqlite", "duckdb") and ds.path:
            candidate = Path(ds.path).expanduser()
            if not candidate.is_absolute():
                ds.path = str((base_dir / candidate).resolve())


def load_config(path: str | Path) -> AppConfig:
    """Load, interpolate, and validate the YAML config at `path`."""
    config_path = Path(path).expanduser()
    if not config_path.is_file():
        raise ConfigError(f"config file not found: {config_path}")

    raw = config_path.read_text(encoding="utf-8")

    try:
        data = yaml.safe_load(raw) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"invalid YAML in {config_path}: {exc}") from exc

    data = _interpolate_env(data)

    try:
        config = AppConfig.model_validate(data)
    except Exception as exc:  # pydantic.ValidationError
        raise ConfigError(f"invalid configuration in {config_path}: {exc}") from exc

    config.app.cache_dir = config.app.cache_dir.expanduser()
    config.app.results_dir = config.app.results_dir.expanduser()
    _resolve_file_paths(config, config_path.parent)
    return config


def save_config(config: AppConfig, path: str | Path) -> None:
    """Atomically write `config` back to `path` as YAML."""
    config_path = Path(path).expanduser()
    payload = config.model_dump(mode="json", exclude_none=True)

    fd, tmp_name = tempfile.mkstemp(
        dir=config_path.parent, prefix=f".{config_path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            yaml.safe_dump(payload, handle, sort_keys=False, default_flow_style=False)
        os.replace(tmp_name, config_path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise
