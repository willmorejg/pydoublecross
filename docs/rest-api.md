# REST API

Built with FastAPI, mounted at `/api/...`; interactive docs are available at `/docs` (Swagger UI)
and `/redoc` while the server is running.

```bash
uv run pydoublecross serve -c my_config.yaml
```

## Endpoints

### Data sources

| Method | Path | Notes |
|---|---|---|
| `GET` | `/api/datasources` | Summary list |
| `GET` | `/api/datasources/{name}` | Full definition; `password` is masked as `***` if set |
| `PUT` | `/api/datasources/{name}` | Create or update; body is a `DataSourceConfig` |
| `DELETE` | `/api/datasources/{name}` | 409 if referenced by a validation item |
| `POST` | `/api/datasources/{name}/test` | Connect and run `SELECT 1` |

### Validation items

| Method | Path | Notes |
|---|---|---|
| `GET` | `/api/validations` | Summary list |
| `GET` | `/api/validations/{name}` | Full definition |
| `PUT` | `/api/validations/{name}` | Create or update; body is a `ValidationItemConfig` |
| `DELETE` | `/api/validations/{name}` | |
| `POST` | `/api/validations/{name}/run?no_cache=&refresh_cache=` | Runs it, returns a `ValidationRunResult` |
| `GET` | `/api/validations/{name}/results?limit=20` | Run history, most recent first |
| `GET` | `/api/validations/{name}/results/{run_id}` | One stored result |

### Reports and cache

| Method | Path | Notes |
|---|---|---|
| `GET` | `/api/reports/{name}/{run_id}?format=excel` | Downloads the exported report |
| `DELETE` | `/api/cache?data_source=NAME` | Omit `data_source` to clear everything |

### Health

`GET /api/health` → `{"status": "ok", "version": "..."}`. Not covered by the API key check below.

## Writes persist to the config file

`PUT`/`DELETE` on data sources and validation items re-validate the whole config (so you can't,
say, delete a data source still referenced by a validation item) and write it back to the same
YAML file the server was started with, atomically.

## Securing it

If you bind `server.host: 0.0.0.0` (network-reachable, not just this machine), set
`server.api_key` in the config. Every `/api/*` request (except `/api/health`) then requires an
`X-API-Key` header matching it, or gets a `401`. This is a basic shared-secret check, not a full
auth system — for anything internet-facing, put it behind a reverse proxy with real
authentication instead.
