# SPDX-FileCopyrightText: 2026 James G Willmore
# SPDX-License-Identifier: Apache-2.0

"""Maps a configured data source `type` to a SQLAlchemy URL.

One generic, SQLAlchemy-backed `DataSource` (see `base.py`) serves every
supported RDBMS; this module is the only place that knows which driver and
URL shape each `type` needs.
"""

from __future__ import annotations

from sqlalchemy.engine import URL, make_url

from pydoublecross.config.models import DataSourceConfig
from pydoublecross.exceptions import DataSourceError

# type -> SQLAlchemy dialect+driver. azure_sql is wire-compatible with mssql.
_DRIVERNAME = {
    "mssql": "mssql+pyodbc",
    "azure_sql": "mssql+pyodbc",
    "postgresql": "postgresql+psycopg",
    "mysql": "mysql+pymysql",
    "oracle": "oracle+oracledb",
    "sqlite": "sqlite",
    "duckdb": "duckdb",
}

_EXTRA_HINT = {
    "mssql": "mssql",
    "azure_sql": "mssql",
    "postgresql": "postgres",
    "mysql": "mysql",
    "oracle": "oracle",
    "duckdb": "duckdb",
}

_DEFAULT_PORT = {
    "mssql": 1433,
    "azure_sql": 1433,
    "postgresql": 5432,
    "mysql": 3306,
    "oracle": 1521,
}


def build_url(config: DataSourceConfig) -> URL:
    """Build a SQLAlchemy URL for a data source configuration.

    If `config.url` is set, it is used as-is (already validated as parseable
    when the config was loaded) and every individual field below is ignored.
    """
    if config.url:
        return make_url(config.url)

    try:
        drivername = _DRIVERNAME[config.type]
    except KeyError as exc:
        raise DataSourceError(f"unsupported data source type '{config.type}'") from exc

    if config.type in ("sqlite", "duckdb"):
        return URL.create(drivername, database=config.path)

    query = dict(config.extra_params)
    if config.type in ("mssql", "azure_sql") and config.driver:
        query["driver"] = config.driver

    return URL.create(
        drivername,
        username=config.username,
        password=config.password,
        host=config.host,
        port=config.port or _DEFAULT_PORT.get(config.type),
        database=config.database,
        query=query,
    )


def missing_driver_hint(config: DataSourceConfig) -> str | None:
    """Return the `pip install` extra name for `config.type`, if any."""
    extra = _EXTRA_HINT.get(config.type)
    if extra is None:
        return None
    return f'pip install "pydoublecross[{extra}]"'
