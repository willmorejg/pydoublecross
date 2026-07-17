# SPDX-FileCopyrightText: 2026 James G Willmore
# SPDX-License-Identifier: Apache-2.0

"""Process bootstrap settings, sourced from the environment.

These are distinct from the YAML-driven :class:`pydoublecross.config.models.AppConfig`:
they only control *how the process starts* (which config file to load, at what log
level) before that YAML has even been read.
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class RuntimeSettings(BaseSettings):
    """Environment-derived bootstrap settings (prefix ``PYDOUBLECROSS_``)."""

    model_config = SettingsConfigDict(env_prefix="PYDOUBLECROSS_", extra="ignore")

    config_path: Path = Path("config/example.yaml")
    log_level: str = "INFO"


runtime_settings = RuntimeSettings()
