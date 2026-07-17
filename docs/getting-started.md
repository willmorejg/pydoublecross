# Getting Started

## Install

pyDoubleCross uses [uv](https://docs.astral.sh/uv/) for environment and dependency management.

```bash
git clone <your fork/repo>
cd pydoublecross
uv sync
```

This installs the core package plus the dev tool group (`ruff`, `ty`, `pytest`, `mkdocs`, ...).
Database drivers are optional extras — install what you actually need:

```bash
uv sync --extra postgres        # PostgreSQL / Azure Database for PostgreSQL
uv sync --extra mssql           # SQL Server / Azure SQL Database
uv sync --extra mysql           # MySQL / Azure Database for MySQL
uv sync --extra oracle          # Oracle
uv sync --extra duckdb          # DuckDB
uv sync --extra all             # everything
```

SQLite needs no extra — it's in the Python standard library.

## Try it against the example config

[`config/example.yaml`](https://github.com/willmorejg/pydoublecross/blob/main/config/example.yaml)
documents the full schema with one SQLite/DuckDB example plus commented-out examples for every
server-based engine.

```bash
uv run pydoublecross validate-config -c config/example.yaml
uv run pydoublecross list -c config/example.yaml
```

## Your first validation item

1. Create two SQLite databases (or point at real ones) with a comparable table.
2. Write a minimal config:

```yaml
app:
  cache_dir: ~/.pydoublecross/cache
  results_dir: ~/.pydoublecross/results

data_sources:
  src:
    type: sqlite
    path: ./legacy.db
  tgt:
    type: sqlite
    path: ./warehouse.db

validations:
  customers:
    source:
      data_source: src
      table: customers
    target:
      data_source: tgt
      table: customers
    key_columns: [customer_id]
```

3. Run it:

```bash
uv run pydoublecross run customers -c my_config.yaml --export excel
```

This prints a summary to the console and writes `customers_<run_id>.xlsx` with the full detail
(see [Reporting](reporting.md)).

4. Or serve it as an API + web app instead:

```bash
uv run pydoublecross serve -c my_config.yaml
# open http://127.0.0.1:8000
```

See [Configuration](configuration.md) for the full schema, or jump straight to
[CLI](cli.md), [REST API](rest-api.md), or [Web UI](web-ui.md).
