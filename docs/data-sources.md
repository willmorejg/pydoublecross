# Data Sources

Every supported RDBMS goes through one SQLAlchemy-backed `DataSource` class
(`pydoublecross.datasources.base.DataSource`); `type` just selects the dialect/driver and how the
connection URL is built (`pydoublecross.datasources.registry`).

| `type`         | Driver                    | Extra to install              | Notes |
|----------------|---------------------------|--------------------------------|-------|
| `sqlite`       | stdlib `sqlite3`          | none                            | `path` required |
| `duckdb`       | `duckdb` + `duckdb-engine`| `pydoublecross[duckdb]`         | `path` required; natural future gateway to Parquet/S3/Iceberg |
| `mssql`        | `pyodbc`                  | `pydoublecross[mssql]`          | needs a system ODBC driver installed (e.g. `msodbcsql18`) |
| `azure_sql`    | `pyodbc`                  | `pydoublecross[mssql]`          | alias of `mssql` — Azure SQL Database is wire-compatible |
| `postgresql`   | `psycopg` (v3)            | `pydoublecross[postgres]`       | also used for Azure Database for PostgreSQL |
| `mysql`        | `pymysql`                 | `pydoublecross[mysql]`          | also used for Azure Database for MySQL |
| `oracle`       | `oracledb` (thin mode)    | `pydoublecross[oracle]`         | no Oracle client install needed |

## File-based (`sqlite`, `duckdb`)

```yaml
warehouse:
  type: duckdb
  path: ./examples/warehouse.duckdb
```

A relative `path` is resolved against the directory containing the config file, not the current
working directory, so configs are portable regardless of where you run the CLI from.

## Server-based (everything else)

```yaml
crm_mssql:
  type: mssql
  host: crm-sql.internal.example.com
  port: 1433              # optional; defaults per type (1433/5432/3306/1521)
  database: crm
  username: svc_pydoublecross
  password: ${env:CRM_MSSQL_PASSWORD}
  driver: "ODBC Driver 18 for SQL Server"   # mssql/azure_sql only
  extra_params:
    TrustServerCertificate: "yes"           # passed through as URL query params
```

`extra_params` is how you pass anything dialect-specific — `sslmode` for PostgreSQL,
TLS options for MySQL, etc.

## Azure

Azure SQL Database is `type: azure_sql` (identical fields to `mssql`). Azure Database for
PostgreSQL/MySQL are just `type: postgresql`/`mysql` with the appropriate `host` and (usually)
an `sslmode`/TLS entry in `extra_params` — there's no separate Azure adapter to configure.

## Testing a connection

```bash
uv run pydoublecross test-connection crm_mssql -c my_config.yaml
```

or `POST /api/datasources/{name}/test`, or the "Test connection" button on the Data Sources page
in the web UI.
