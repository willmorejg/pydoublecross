# SPDX-FileCopyrightText: 2026 James G Willmore
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pydoublecross.config.models import DataSourceConfig
from pydoublecross.datasources.registry import build_url, missing_driver_hint


def test_sqlite_url() -> None:
    config = DataSourceConfig(type="sqlite", path="/opt/pydoublecross/foo.db")
    url = build_url(config)
    assert url.drivername == "sqlite"
    assert url.database == "/opt/pydoublecross/foo.db"


def test_duckdb_url() -> None:
    config = DataSourceConfig(type="duckdb", path="/opt/pydoublecross/foo.duckdb")
    url = build_url(config)
    assert url.drivername == "duckdb"


def test_postgresql_url_default_port() -> None:
    config = DataSourceConfig(type="postgresql", host="db.example.com", database="analytics")
    url = build_url(config)
    assert url.drivername == "postgresql+psycopg"
    assert url.port == 5432
    assert url.host == "db.example.com"


def test_mssql_url_includes_driver_query_param() -> None:
    config = DataSourceConfig(
        type="mssql",
        host="sql.example.com",
        driver="ODBC Driver 18 for SQL Server",
        extra_params={"TrustServerCertificate": "yes"},
    )
    url = build_url(config)
    assert url.drivername == "mssql+pyodbc"
    assert url.query["driver"] == "ODBC Driver 18 for SQL Server"
    assert url.query["TrustServerCertificate"] == "yes"


def test_azure_sql_aliases_to_mssql_driver() -> None:
    config = DataSourceConfig(type="azure_sql", host="azsql.example.com")
    url = build_url(config)
    assert url.drivername == "mssql+pyodbc"


def test_missing_driver_hint_for_oracle() -> None:
    config = DataSourceConfig(type="oracle", host="ora.example.com")
    hint = missing_driver_hint(config)
    assert hint is not None
    assert "oracle" in hint


def test_missing_driver_hint_none_for_sqlite() -> None:
    config = DataSourceConfig(type="sqlite", path="/opt/pydoublecross/foo.db")
    assert missing_driver_hint(config) is None


def test_raw_url_takes_precedence_over_individual_fields() -> None:
    config = DataSourceConfig(
        type="postgresql",
        url="postgresql+psycopg://alice:secret@pg.example.com:5433/analytics?sslmode=require",
        host="ignored.example.com",
        username="ignored",
    )
    url = build_url(config)
    assert url.drivername == "postgresql+psycopg"
    assert url.host == "pg.example.com"
    assert url.port == 5433
    assert url.username == "alice"
    assert url.database == "analytics"
    assert url.query["sslmode"] == "require"


def test_raw_url_for_sqlite_bypasses_path_requirement() -> None:
    config = DataSourceConfig(type="sqlite", url="sqlite:////opt/pydoublecross/foo.db")
    url = build_url(config)
    assert url.drivername == "sqlite"
    assert url.database == "/opt/pydoublecross/foo.db"
