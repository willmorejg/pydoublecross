# CLI

Every command takes `-c/--config` (default `config/example.yaml`).

```bash
uv run pydoublecross --help
```

## Commands

| Command | Purpose |
|---|---|
| `validate-config` | Load and validate the config, exit 0/1. Does not connect to any data source. |
| `list` | Table of configured validation items. |
| `run <item>` | Run one validation item. Exit code 1 if the result isn't `passed`. |
| `run-all` | Run every configured validation item. Exit code 1 if any isn't `passed`. |
| `test-connection <data_source>` | Connect and run `SELECT 1` against a named data source. |
| `cache clear [--data-source NAME]` | Clear cached query results, optionally scoped to one data source. |
| `serve` | Run the combined REST API + web UI (see [REST API](rest-api.md) / [Web UI](web-ui.md)). |
| `version` | Print the installed version. |

## `run` options

```bash
uv run pydoublecross run customer_check -c my_config.yaml \
  --no-cache               # or --refresh-cache, see Caching
  --export excel --output report   # writes report.xlsx
```

`run` and `run-all` print a summary table plus per-side GE pass/fail counts to the console
(via `rich`) and exit non-zero on failure — convenient for CI: a failed reconciliation fails
the pipeline.

## `serve` options

```bash
uv run pydoublecross serve -c my_config.yaml --host 0.0.0.0 --port 8000 --reload
```

`--host`/`--port` override `server.host`/`server.port` from the config. `--reload` is for local
development only (auto-restarts on source changes; don't use it in production).
