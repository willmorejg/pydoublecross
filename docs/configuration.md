# Configuration

Everything is one YAML file, loaded via `-c/--config` on the CLI or `PYDOUBLECROSS_CONFIG_PATH`
for the API/web server. See [`config/example.yaml`](https://github.com/willmorejg/pydoublecross/blob/main/config/example.yaml)
for a complete, commented reference.

## Top-level sections

```yaml
app:
  name: pyDoubleCross
  cache_dir: ~/.pydoublecross/cache
  results_dir: ~/.pydoublecross/results
  log_level: INFO

server:
  host: 127.0.0.1   # 127.0.0.1 = this machine only; 0.0.0.0 = network-reachable
  port: 8000
  api_key: null      # optional, see below

data_sources: { ... }
validations: { ... }
```

## Secrets

Never write a password in plaintext. Reference an environment variable instead:

```yaml
password: ${env:CRM_MSSQL_PASSWORD}
```

This is substituted before the YAML is parsed; if the variable isn't set, the config fails to
load with a clear error rather than connecting with a literal `${env:...}` string.

## Data sources

Each entry under `data_sources` is a named, reusable connection. See [Data Sources](data-sources.md)
for the fields each `type` needs, and [Caching](caching.md) for the `cache` block.

## Validation items

Each entry under `validations` pairs a `source` and a `target` — both are *references* to a named
data source, not new connections:

```yaml
validations:
  customer_count_check:
    description: "Reconcile customer records"
    source:
      data_source: legacy_sqlite
      sql: "SELECT customer_id, name, email, status FROM customers"
    target:
      data_source: warehouse_duckdb
      table: dim_customers        # table shorthand for SELECT * FROM <table>
      cache:
        enabled: false            # per-reference cache override, see Caching
    key_columns: [customer_id]
    compare_columns: [name, email, status]   # omit to compare all common columns
    ignore_columns: []
    numeric_tolerance: 0.0        # abs(source - target) <= tolerance is not a mismatch
    expectations:
      row_count_match: true       # each side's row count must be > 0
      schema_match: true          # each side's columns must match its query's columns
      null_checks: true           # flag unexpected nulls per column, per side
```

`source`/`target` each need exactly one of `sql` or `table`.

## Server-side edits

The REST API and web UI can create, edit, and delete data sources and validation items — those
changes are validated the same way as the file on disk and written back to the same config file
(atomically). If you hand-edit the file while the server is running, restart it to pick up the
change; there's no file-watching.
