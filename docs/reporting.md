# Reporting

Every run produces a `ValidationRunResult` (see `pydoublecross.validation.results`), persisted as
JSON under `app.results_dir/<item_name>/<run_id>.json` so it can be re-fetched later from the CLI,
API, or web UI without re-running the validation.

## Fields

- `summary` — row counts (source, target, matched, missing-in-target, missing-in-source,
  mismatched rows/cells)
- `missing_in_target` / `missing_in_source` — sample key values (capped at 200)
- `mismatches` — sample `{key, column, source_value, target_value}` rows (capped at 200)
- `ge_results` — per-side Great Expectations outcome
- `truncated` — true if any sample list above was cut off; the summary counts themselves are
  always exact and uncapped
- `source_cache_hit` / `target_cache_hit` — whether each side was served from cache

## Exporting

Currently one format: Excel, via `pydoublecross.reporting.exporters.excel.ExcelExporter`. A
workbook with five sheets:

| Sheet | Contents |
|-------|----------|
| Summary | run metadata + the `summary` counts |
| Missing In Target | sample rows present in source, absent in target |
| Missing In Source | sample rows present in target, absent in source |
| Value Mismatches | sample `key` / `column` / `source_value` / `target_value` rows |
| GE Expectations | per-side pass/fail counts and which expectation types failed |

```bash
uv run pydoublecross run customer_check -c my_config.yaml --export excel --output report
# -> report.xlsx
```

or `GET /api/reports/{item}/{run_id}?format=excel`, or the "Export to Excel" link on a result page
in the web UI.

## Adding another format

`pydoublecross.reporting.exporters.base.Exporter` is a small ABC (`export(result, destination) ->
Path`); register a new implementation in `pydoublecross.reporting.exporters.EXPORTERS` to expose
it through the CLI's `--export`, the API's `?format=`, and the web UI at the same time — none of
them know about export formats directly, they all go through
`ValidationRunner.export(result, fmt, destination)`.
