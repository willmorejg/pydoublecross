# SPDX-FileCopyrightText: 2026 James G Willmore
# SPDX-License-Identifier: Apache-2.0

"""Pydantic models for the YAML configuration schema."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

DataSourceType = Literal[
    "mssql",
    "azure_sql",
    "postgresql",
    "mysql",
    "oracle",
    "sqlite",
    "duckdb",
]


class CacheDefaults(BaseModel):
    """Default caching behavior declared on a named data source."""

    enabled: bool = False
    ttl_seconds: int = 3600


class CacheOverride(BaseModel):
    """Per-reference override of a data source's cache defaults.

    Lets the same data source be cached when used as one validation item's
    source but bypassed when used as another's target (or vice versa).
    """

    enabled: bool | None = None
    ttl_seconds: int | None = None
    force_refresh: bool = False

    def resolve(self, defaults: CacheDefaults) -> ResolvedCacheOptions:
        return ResolvedCacheOptions(
            enabled=self.enabled if self.enabled is not None else defaults.enabled,
            ttl_seconds=self.ttl_seconds if self.ttl_seconds is not None else defaults.ttl_seconds,
            force_refresh=self.force_refresh,
        )


class ResolvedCacheOptions(BaseModel):
    """The final cache decision for one data source reference in one run."""

    enabled: bool
    ttl_seconds: int
    force_refresh: bool = False


class DataSourceConfig(BaseModel):
    """A named, reusable connection definition.

    Either provide `url` (a full SQLAlchemy connection URL, e.g.
    ``postgresql+psycopg://user:pass@host:5432/dbname``) or the individual
    `host`/`port`/`database`/`username`/`password`/`path` fields — not both need
    be fully specified, but `url` always takes precedence when present.
    """

    type: DataSourceType
    url: str | None = None  # raw SQLAlchemy URL; overrides the individual fields below
    host: str | None = None
    port: int | None = None
    database: str | None = None
    username: str | None = None
    password: str | None = None
    path: str | None = None  # file path, for sqlite / duckdb
    driver: str | None = None  # e.g. "ODBC Driver 18 for SQL Server"
    extra_params: dict[str, str] = Field(default_factory=dict)
    cache: CacheDefaults = Field(default_factory=CacheDefaults)

    @model_validator(mode="after")
    def _check_location(self) -> DataSourceConfig:
        if self.url:
            try:
                make_url(self.url)
            except ArgumentError as exc:
                raise ValueError(f"invalid 'url': {exc}") from exc
            return self

        file_based = self.type in ("sqlite", "duckdb")
        if file_based and not self.path:
            raise ValueError(f"data source of type '{self.type}' requires 'path' (or 'url')")
        if not file_based and not self.host:
            raise ValueError(f"data source of type '{self.type}' requires 'host' (or 'url')")
        return self


class DataSourceRef(BaseModel):
    """How a validation item references a data source, as its source or target."""

    data_source: str
    sql: str | None = None
    table: str | None = None
    cache: CacheOverride = Field(default_factory=CacheOverride)

    @model_validator(mode="after")
    def _check_query(self) -> DataSourceRef:
        if bool(self.sql) == bool(self.table):
            raise ValueError("exactly one of 'sql' or 'table' must be set")
        return self

    @property
    def query(self) -> str:
        if self.sql:
            return self.sql
        return f"SELECT * FROM {self.table}"


class ExpectationToggles(BaseModel):
    """Which built-in Great Expectations checks to run per side."""

    row_count_match: bool = True
    schema_match: bool = True
    null_checks: bool = True


class ValidationItemConfig(BaseModel):
    """A named comparison between a source and a target data source."""

    description: str | None = None
    source: DataSourceRef
    target: DataSourceRef
    key_columns: list[str]
    compare_columns: list[str] | None = None
    ignore_columns: list[str] = Field(default_factory=list)
    numeric_tolerance: float = 0.0
    expectations: ExpectationToggles = Field(default_factory=ExpectationToggles)


class AppSection(BaseModel):
    name: str = "pyDoubleCross"
    cache_dir: Path = Path("~/.pydoublecross/cache").expanduser()
    results_dir: Path = Path("~/.pydoublecross/results").expanduser()
    log_level: str = "INFO"


class ServerConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8000
    api_key: str | None = None


class AppConfig(BaseModel):
    """Root configuration document."""

    app: AppSection = Field(default_factory=AppSection)
    server: ServerConfig = Field(default_factory=ServerConfig)
    data_sources: dict[str, DataSourceConfig] = Field(default_factory=dict)
    validations: dict[str, ValidationItemConfig] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check_references(self) -> AppConfig:
        for item_name, item in self.validations.items():
            for role, ref in (("source", item.source), ("target", item.target)):
                if ref.data_source not in self.data_sources:
                    raise ValueError(
                        f"validation '{item_name}' {role} references unknown "
                        f"data source '{ref.data_source}'"
                    )
        return self

    def resolve_cache(self, ref: DataSourceRef) -> ResolvedCacheOptions:
        """Resolve a reference's effective cache options against its data source's defaults."""
        defaults = self.data_sources[ref.data_source].cache
        return ref.cache.resolve(defaults)
