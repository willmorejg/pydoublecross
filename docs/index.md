# pyDoubleCross

pyDoubleCross validates data consistency between a **source** and a **target** data source.
Point it at two RDBMS connections (or the same one twice), define a comparison by key column,
and it tells you exactly which rows are missing, which are extra, and which values disagree —
plus runs a set of schema/nullness sanity checks on each side with
[Great Expectations](https://greatexpectations.io/).

## Why

Data migrations, ETL pipelines, and system cutovers all share the same question: *does the data
in system B actually match system A?* pyDoubleCross automates answering that, repeatedly, without
writing one-off comparison scripts per migration.

## Supported data sources

Today: MS SQL Server, Azure SQL Database, PostgreSQL (incl. Azure Database for PostgreSQL),
MySQL (incl. Azure Database for MySQL), Oracle, SQLite, DuckDB — all through one
SQLAlchemy-backed connector (see [Data Sources](data-sources.md)).

Planned: S3, Iceberg, Databricks.

## Three ways to run it

- [CLI](cli.md) — `pydoublecross run <item>`, scriptable, CI-friendly.
- [REST API](rest-api.md) — FastAPI, for integrating into other tooling.
- [Web UI](web-ui.md) — server-rendered pages for defining and running validations without the
  command line, in the same process as the API.

## Core ideas

- **Validation items** are named comparisons: a [source and a target data source
  reference](configuration.md#validation-items), a set of key columns, and which columns to
  compare.
- **Caching** is per data-source-reference, not global: the same data source can be cached when
  used as one item's source and bypassed when used as another's target. See [Caching](caching.md).
- **Validation** combines per-side Great Expectations checks with a dedicated pandas-based
  key-column diff — see [Validation](validation.md) for why those are two separate things.
- **Reports** are generated per run and exportable to Excel — see [Reporting](reporting.md).

Start with [Getting Started](getting-started.md).

## License

Apache License 2.0 — see [License](license.md).
