# Caching

Fetching a large table for every validation run is often wasteful, especially while iterating on
a comparison's key/compare columns. pyDoubleCross can cache each side's query result as Parquet
and reuse it until it expires or is explicitly refreshed.

## It's per reference, not per data source

Caching is configured in two layers:

1. **Defaults**, on the data source itself:

   ```yaml
   data_sources:
     legacy_sqlite:
       type: sqlite
       path: ./legacy.db
       cache:
         enabled: true
         ttl_seconds: 3600
   ```

2. **Overrides**, on each validation item's reference to that data source:

   ```yaml
   validations:
     customer_check:
       source:
         data_source: legacy_sqlite
         table: customers
         # no override -> inherits legacy_sqlite's default (enabled, 1h TTL)
       target:
         data_source: legacy_sqlite   # same data source, used again
         table: audit_log
         cache:
           enabled: false             # override: never cache this particular query
   ```

This is why the same data source can be cached in one validation item and always-fresh in
another — the cache decision is resolved per `(validation item, source-or-target)` pair, not
per data source.

## Cache key

The cache key is `sha256(data_source_name + resolved_query)[:16]`, stored under
`app.cache_dir/<data_source_name>/<hash>.parquet` plus a `.json` metadata sidecar (fetch
timestamp, row count). Two validation items querying the same data source with the same SQL share
a cache entry; different SQL (or a different `table`) gets a different entry.

## Overriding at run time

Every entry point supports bypassing or force-refreshing the cache for one run, without changing
the config:

- CLI: `pydoublecross run <item> --no-cache` or `--refresh-cache`
- REST: `POST /api/validations/{name}/run?no_cache=true` or `?refresh_cache=true`
- Web: the validation editor's per-side cache dropdown includes a "force refresh on next run"
  checkbox

`--no-cache`/`no_cache` bypasses both reading and writing the cache for that run. `--refresh-cache`
skips the read but still writes a fresh entry, so subsequent runs are served from the refreshed
cache.

## Clearing the cache

```bash
uv run pydoublecross cache clear -c my_config.yaml                  # everything
uv run pydoublecross cache clear -c my_config.yaml --data-source src  # one data source
```

or `DELETE /api/cache?data_source=src`.
