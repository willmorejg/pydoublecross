# Web UI

Server-rendered pages (Jinja2 + a touch of [HTMX](https://htmx.org/) for the "test connection"
button), mounted in the same FastAPI app as the REST API — one process, one `serve` command.

```bash
uv run pydoublecross serve -c my_config.yaml
# open http://127.0.0.1:8000
```

## Pages

- **Dashboard** (`/`) — every validation item, its last run status, and Run / Edit / History /
  Delete actions.
- **Data Sources** (`/datasources`) — list, create, edit, delete, test connection.
- **New/Edit Validation** (`/validations/new`, `/validations/{name}/edit`) — the source and target
  definitions side by side, each with its own data source picker, SQL/table input, and cache
  override — mirroring the config schema described in [Configuration](configuration.md).
- **Result** (`/validations/{name}/results/{run_id}`) — summary cards, GE outcomes, mismatch and
  missing-row tables, Excel export link.
- **History** (`/validations/{name}/results`) — past runs for one item.

## Single machine vs. network-reachable

`server.host: 127.0.0.1` (the default) means only this machine can reach it — fine for a personal
or single-operator setup. Set it to `0.0.0.0` to make it reachable on the network; if you do,
also set `server.api_key` (see [REST API](rest-api.md#securing-it)) and consider putting it behind
a reverse proxy, since the web UI itself has no login/session system.

## It's the same engine as the CLI and API

Every page action (create, run, delete) goes through the same `ValidationRunner` the CLI and REST
API use — there's no separate web-only logic, so behavior (caching rules, validation status,
report contents) is identical across all three front ends.
