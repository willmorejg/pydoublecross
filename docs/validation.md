# Validation

A validation run combines two distinct kinds of checks, because they answer different questions.

## Per-side checks (Great Expectations and/or Pandera)

Both [Great Expectations](https://greatexpectations.io/) and [Pandera](https://pandera.readthedocs.io/)
validate *one batch* against a schema/suite — neither compares two batches to each other, that's
the job of [cross-source comparison](#cross-source-comparison-pandas) below. So for each side
(source and target) independently, pyDoubleCross runs a small check set controlled by the item's
`expectations` block, using whichever engine(s) `validation_engine` selects:

| `expectations` toggle | Great Expectations | Pandera |
|---|---|---|
| `row_count_match` | `ExpectTableRowCountToBeBetween(min_value=1)` | dataframe-level `Check(len(df) > 0)` |
| `schema_match` | `ExpectTableColumnsToMatchSet` | `DataFrameSchema(..., strict=True)` |
| `null_checks` | `ExpectColumnValuesToNotBeNull` per column | `Column(nullable=False)` per column |

Both engines skip the null check for columns that are *entirely* null (treated as intentional,
not flagged). This catches "this side of the query is obviously broken" problems (empty result,
missing column, a formerly-populated column that's now all NULL) independently of the other side.

`validation_engine` (per validation item) is one of:

- `great_expectations` (default) — only GE runs
- `pandera` — only Pandera runs; lighter weight, pure-Python, no ephemeral GX context per run
- `both` — both run, independently, and both must pass for the item to pass; results from both
  show up side by side (tagged by `engine`) in the run result, report, and Excel export

The `expectations` toggles mean the same thing regardless of engine, so switching
`validation_engine` doesn't change *what's* checked, only which library checks it — useful for
cross-checking one engine's result against the other, or for picking whichever is lighter/faster
for your use case. Note `schema_match` has the same limitation on both engines: there's no
separately-declared "expected schema" to diff against yet, so it only catches gross structural
problems (e.g. a column dropping out mid-run), not schema *drift* against some prior baseline.

## Cross-source comparison (pandas)

The actual "does source match target" question — missing rows, extra rows, mismatched values —
is answered by `pydoublecross.validation.comparators.compare_dataframes`, not by GX:

1. Both dataframes are indexed by `key_columns`, using a *normalized* form of each key value for
   matching purposes only (see [Key type normalization](#key-type-normalization) below). Duplicate
   keys on either side raise an error immediately (silently picking one row would produce a
   misleading diff).
2. Keys present only in source → **missing in target**; only in target → **missing in source**.
3. For keys present on both sides, each `compare_columns` entry (default: every column present
   in both, minus keys and `ignore_columns`) is compared:
      - numeric columns use `numeric_tolerance` (`abs(source - target) <= tolerance` is not a
        mismatch)
      - everything else compares as strings, whitespace-trimmed (see
        [Key type normalization](#key-type-normalization) — the same fixed-width `CHAR` padding
        problem shows up here too, e.g. `"producer"` vs `"producer   "`), after normalizing
        both-null to "equal"
      - one side null and the other not is always a mismatch
      - this is case-*sensitive* — `"Producer"` vs `"producer"` is still a mismatch, only
        whitespace is forgiven
4. Missing-row and mismatch samples are capped (200 rows each) with `truncated: true` set on the
   result if anything was cut off — full row/mismatch counts in the summary are never capped.

## Key type normalization

The same underlying problem — one side's driver/column type not matching the other's — shows up
in two places: matching rows to each other (this section), and comparing non-key column values
once rows are matched (the whitespace-trimming note above). Both exist for the same reason.

Different databases (and even different drivers for the same database) routinely return "the
same" key value as different Python types — an `INTEGER` column might come back as `int`,
`numpy.int64`, or `decimal.Decimal` depending on the driver, and a legacy system's ID might be a
`VARCHAR` where the current one is numeric. Matched against each other with strict equality, `1`,
`"1"`, and `Decimal("1.00")` would never be considered the same row — every one of those rows
would show up as **missing on both sides**, even though source and target agree.

To avoid that, key values are normalized *only for matching purposes* before the join:

- Numbers (`int`, `float`, `Decimal`, and numeric-looking strings) are compared by numeric value
  via `Decimal` — no floating-point rounding, so `1`, `1.0`, `"1"`, and `Decimal("1.00")` are all
  the same key.
- Non-numeric strings are whitespace-trimmed (handles fixed-width `CHAR` columns padded with
  trailing spaces on one side).
- Everything else (dates, booleans, etc.) is compared as-is.

This normalization affects *only* whether two rows are considered "the same row" — the
`key`/`source_value`/`target_value` fields in results always show the original, unnormalized
value each side actually returned, so a genuine type or formatting difference is still visible
if you go looking for it; it just won't be misreported as a missing row. If you were adding
`CAST`/`CONVERT` to your source/target SQL to work around this, you generally don't need to
anymore — key matching handles it automatically.

## Status

A run is `passed` only if every per-side check from every selected engine succeeded *and* the
comparison found zero missing/mismatched rows. Otherwise it's `failed`, or `error` if the run
couldn't complete (bad
SQL, connection failure, misconfigured key columns, etc. — the error message is captured on the
result instead of raising past the API/CLI boundary).

## Composite keys

`key_columns` can list more than one column; the diff and mismatch samples key on the tuple.
