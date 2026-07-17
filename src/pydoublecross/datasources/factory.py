# SPDX-FileCopyrightText: 2026 James G Willmore
# SPDX-License-Identifier: Apache-2.0

"""Build `DataSource` instances from configuration."""

from __future__ import annotations

from pydoublecross.config.models import AppConfig
from pydoublecross.datasources.base import DataSource
from pydoublecross.exceptions import DataSourceError


class DataSourceFactory:
    """Creates and caches `DataSource` instances for one loaded `AppConfig`."""

    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._instances: dict[str, DataSource] = {}

    def get(self, name: str) -> DataSource:
        if name not in self._instances:
            try:
                ds_config = self._config.data_sources[name]
            except KeyError as exc:
                raise DataSourceError(f"unknown data source '{name}'") from exc
            self._instances[name] = DataSource(name, ds_config)
        return self._instances[name]

    def dispose_all(self) -> None:
        for instance in self._instances.values():
            instance.dispose()
        self._instances.clear()
