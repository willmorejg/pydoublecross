# Validation

A validation run combines two distinct kinds of checks, because they answer different questions.

## Per-side checks (Great Expectations)

[Great Expectations](https://greatexpectations.io/) validates *one batch* against a suite of
expectations — it doesn't compare two batches to each other. So for each side (source and
target) independently, pyDoubleCross builds an ephemeral GX context, registers the fetched
dataframe as a pandas data asset, and runs a small suite controlled by the item's `expectations`
block:

- `row_count_match` → `ExpectTableRowCountToBeBetween(min_value=1)` — the side isn't empty
- `schema_match` → `ExpectTableColumnsToMatchSet` — the columns are what the query said they'd be
- `null_checks` → `ExpectColumnValuesToNotBeNull` per column, skipping columns that are *entirely*
  null (treated as intentional, not flagged)

This catches "this side of the query is obviously broken" problems (empty result, missing
column, a formerly-populated column that's now all NULL) independently of the other side.

## Cross-source comparison (pandas)

The actual "does source match target" question — missing rows, extra rows, mismatched values —
is answered by `pydoublecross.validation.comparators.compare_dataframes`, not by GX:

1. Both dataframes are indexed by `key_columns`. Duplicate keys on either side raise an error
   immediately (silently picking one row would produce a misleading diff).
2. Keys present only in source → **missing in target**; only in target → **missing in source**.
3. For keys present on both sides, each `compare_columns` entry (default: every column present
   in both, minus keys and `ignore_columns`) is compared:
      - numeric columns use `numeric_tolerance` (`abs(source - target) <= tolerance` is not a
        mismatch)
      - everything else compares as strings after normalizing both-null to "equal"
      - one side null and the other not is always a mismatch
4. Missing-row and mismatch samples are capped (200 rows each) with `truncated: true` set on the
   result if anything was cut off — full row/mismatch counts in the summary are never capped.

## Status

A run is `passed` only if every per-side GX check succeeded *and* the comparison found zero
missing/mismatched rows. Otherwise it's `failed`, or `error` if the run couldn't complete (bad
SQL, connection failure, misconfigured key columns, etc. — the error message is captured on the
result instead of raising past the API/CLI boundary).

## Composite keys

`key_columns` can list more than one column; the diff and mismatch samples key on the tuple.
