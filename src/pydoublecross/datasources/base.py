# SPDX-FileCopyrightText: 2026 James G Willmore
# SPDX-License-Identifier: Apache-2.0

"""Generic SQLAlchemy-backed data source."""

from __future__ import annotations

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from pydoublecross.config.models import DataSourceConfig
from pydoublecross.datasources.registry import build_url, missing_driver_hint
from pydoublecross.exceptions import DataSourceError


class DataSource:
    """Wraps one named connection; every supported RDBMS type uses this class."""

    def __init__(self, name: str, config: DataSourceConfig) -> None:
        self.name = name
        self.config = config
        self._engine: Engine | None = None

    @property
    def engine(self) -> Engine:
        if self._engine is None:
            self._engine = self._create_engine()
        return self._engine

    def _create_engine(self) -> Engine:
        url = build_url(self.config)
        try:
            return create_engine(url)
        except ModuleNotFoundError as exc:
            hint = missing_driver_hint(self.config)
            suffix = f" Install the driver with: {hint}" if hint else ""
            raise DataSourceError(
                f"missing driver for data source '{self.name}' (type={self.config.type}).{suffix}"
            ) from exc

    def test_connection(self) -> bool:
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as exc:
            raise DataSourceError(f"connection test failed for '{self.name}': {exc}") from exc

    def fetch_dataframe(self, sql: str) -> pd.DataFrame:
        try:
            with self.engine.connect() as conn:
                return pd.read_sql(text(sql), conn)
        except DataSourceError:
            raise
        except Exception as exc:
            raise DataSourceError(f"query failed on data source '{self.name}': {exc}") from exc

    def dispose(self) -> None:
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None
