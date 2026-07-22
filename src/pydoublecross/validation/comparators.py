# SPDX-FileCopyrightText: 2026 James G Willmore
# SPDX-License-Identifier: Apache-2.0

"""Pandas-based, key-column row/value comparison between two dataframes.

This is deliberately separate from Great Expectations: GE validates one
batch against a suite of expectations, it does not diff two batches against
each other. Cross-source row and value comparison lives here instead.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

import numpy as np
import pandas as pd

from pydoublecross.exceptions import ValidationEngineError
from pydoublecross.validation.results import (
    MAX_SAMPLE_ROWS,
    ColumnMismatch,
    ComparisonOutcome,
    ComparisonSummary,
)


def _to_native(value: object) -> object:
    """Convert numpy/pandas scalars to plain Python types so results are JSON-serializable."""
    if isinstance(value, np.generic):
        value = value.item()
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return value


def _normalize_key_value(value: object) -> object:
    """Canonicalize one key value for row-matching, independent of its source dtype.

    Different databases/drivers routinely return "the same" key as different Python
    types - int vs numpy.int64 vs Decimal vs a numeric string, or a CHAR column
    padded with trailing spaces vs an unpadded VARCHAR. Matching those with strict
    `==`/hashing (as a plain `set_index` would) makes every such row look "missing"
    on both sides. Numbers are normalized via `Decimal` (exact, no float rounding);
    strings are whitespace-trimmed. The original, unnormalized values are still what
    gets shown in results - this only affects which rows are considered the same row.
    """
    if isinstance(value, np.generic):
        value = value.item()
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, str):
        text = value.strip()
        try:
            return Decimal(text)
        except InvalidOperation:
            return text
    return value


def _normalized_key_index(frame: pd.DataFrame, key_columns: list[str]) -> pd.Index:
    normalized = [frame[col].map(_normalize_key_value) for col in key_columns]
    if len(key_columns) == 1:
        return pd.Index(normalized[0], name=key_columns[0])
    return pd.MultiIndex.from_arrays(normalized, names=key_columns)


def _case_sensitivity_hint(missing: list[str], *column_sets: pd.Index) -> str:
    """If a "missing" name actually exists under different case, say so explicitly.

    Column name matching (`key_columns`/`compare_columns`/`ignore_columns` against the
    dataframe's actual columns) is case-sensitive - this is the single most common
    reason a name that "should" be there is reported missing.
    """
    notes: dict[str, str] = {}
    for name in missing:
        for columns in column_sets:
            for col in columns:
                if col != name and col.lower() == name.lower():
                    notes.setdefault(name, f"'{name}' configured vs '{col}' actual")
    if not notes:
        return ""
    return f" Column names are matched case-sensitively - found: {', '.join(notes.values())}."


def _resolve_compare_columns(
    source: pd.DataFrame,
    target: pd.DataFrame,
    key_columns: list[str],
    compare_columns: list[str] | None,
    ignore_columns: list[str],
) -> list[str]:
    if compare_columns is not None:
        missing_source = [c for c in compare_columns if c not in source.columns]
        missing_target = [c for c in compare_columns if c not in target.columns]
        if missing_source or missing_target:
            hint = _case_sensitivity_hint(
                missing_source + missing_target, source.columns, target.columns
            )
            raise ValidationEngineError(
                "compare_columns not present in both sides: "
                f"missing_from_source={missing_source} missing_from_target={missing_target}.{hint}"
            )
        return list(compare_columns)

    common = [c for c in source.columns if c in set(target.columns)]
    return [c for c in common if c not in key_columns and c not in ignore_columns]


def _require_columns_present(
    source: pd.DataFrame, target: pd.DataFrame, key_columns: list[str]
) -> None:
    missing_source = [c for c in key_columns if c not in source.columns]
    missing_target = [c for c in key_columns if c not in target.columns]
    if missing_source or missing_target:
        hint = _case_sensitivity_hint(
            missing_source + missing_target, source.columns, target.columns
        )
        raise ValidationEngineError(
            "key_columns not present in both sides: "
            f"missing_from_source={missing_source} missing_from_target={missing_target}.{hint}"
        )


def _require_unique_index(frame: pd.DataFrame, label: str, key_columns: list[str]) -> None:
    dupes = frame.index[frame.index.duplicated()]
    if len(dupes) > 0:
        raise ValidationEngineError(
            f"key_columns {key_columns} are not unique in {label} "
            f"({len(dupes)} duplicate key(s) found)"
        )


def _key_tuple(row: pd.Series, key_columns: list[str]) -> dict[str, object]:
    return {col: _to_native(row[col]) for col in key_columns}


def _sample_missing_rows(
    frame: pd.DataFrame, keys: set, key_columns: list[str]
) -> tuple[list[dict[str, object]], bool]:
    ordered = sorted(keys, key=str)
    truncated = len(ordered) > MAX_SAMPLE_ROWS
    rows = []
    for key in ordered[:MAX_SAMPLE_ROWS]:
        row = frame.loc[key]
        row = row.iloc[0] if isinstance(row, pd.DataFrame) else row
        rows.append(_key_tuple(row, key_columns))
    return rows, truncated


def _column_mismatch_mask(
    src_col: pd.Series, tgt_col: pd.Series, numeric_tolerance: float
) -> pd.Series:
    both_null = src_col.isna() & tgt_col.isna()
    either_null = src_col.isna() ^ tgt_col.isna()

    # Trim whitespace before comparing text: fixed-width CHAR columns padded on one
    # side but not the other (very common when one side is a legacy/mainframe system)
    # would otherwise report every row as mismatched despite looking identical.
    src_str = src_col.astype(str).str.strip()
    tgt_str = tgt_col.astype(str).str.strip()
    string_mismatch = src_str != tgt_str

    # A column can be numeric on one side and text on the other (e.g. one side's
    # driver/query returns "808", the other returns 808.0 as text via a linked
    # server or CAST) - dtype alone can't tell us to compare numerically. Instead,
    # normalize every value the same way key columns are (see `_normalize_key_value`)
    # and compare as numbers wherever both sides parse as one; only genuinely
    # non-numeric values fall back to the (whitespace-trimmed) string comparison.
    normalized_src = src_col.map(_normalize_key_value)
    normalized_tgt = tgt_col.map(_normalize_key_value)
    both_numeric = normalized_src.map(lambda v: isinstance(v, Decimal)) & normalized_tgt.map(
        lambda v: isinstance(v, Decimal)
    )

    numeric_mismatch = pd.Series(False, index=src_col.index)
    if both_numeric.any():
        idx = both_numeric[both_numeric].index
        diffs = (normalized_src.loc[idx] - normalized_tgt.loc[idx]).abs()
        tolerance = Decimal(str(numeric_tolerance))
        numeric_mismatch.loc[idx] = diffs > tolerance

    cell_mismatch = (both_numeric & numeric_mismatch) | (~both_numeric & string_mismatch)
    return either_null | ((~both_null) & cell_mismatch)


def _diff_common_rows(
    src_common: pd.DataFrame,
    tgt_common: pd.DataFrame,
    cols: list[str],
    key_columns: list[str],
    numeric_tolerance: float,
) -> tuple[list[ColumnMismatch], int, int, bool]:
    mismatches: list[ColumnMismatch] = []
    mismatched_cell_count = 0
    truncated = False
    row_mismatch_mask = pd.Series(False, index=src_common.index)

    for col in cols:
        mask = _column_mismatch_mask(src_common[col], tgt_common[col], numeric_tolerance)
        mismatched_cell_count += int(mask.sum())
        row_mismatch_mask |= mask

        for key in src_common.index[mask]:
            row_src = src_common.loc[key]
            row_tgt = tgt_common.loc[key]
            if isinstance(row_src, pd.DataFrame):
                row_src, row_tgt = row_src.iloc[0], row_tgt.iloc[0]
            if len(mismatches) >= MAX_SAMPLE_ROWS:
                truncated = True
                continue
            mismatches.append(
                ColumnMismatch(
                    key=_key_tuple(row_src, key_columns),
                    column=col,
                    source_value=_to_native(row_src[col]),
                    target_value=_to_native(row_tgt[col]),
                )
            )

    return mismatches, mismatched_cell_count, int(row_mismatch_mask.sum()), truncated


def compare_dataframes(
    source: pd.DataFrame,
    target: pd.DataFrame,
    key_columns: list[str],
    compare_columns: list[str] | None = None,
    ignore_columns: list[str] | None = None,
    numeric_tolerance: float = 0.0,
) -> ComparisonOutcome:
    """Diff `source` against `target` by `key_columns`, returning a `ComparisonOutcome`."""
    ignore_columns = ignore_columns or []
    _require_columns_present(source, target, key_columns)
    cols = _resolve_compare_columns(source, target, key_columns, compare_columns, ignore_columns)

    src = source.copy()
    src.index = _normalized_key_index(source, key_columns)
    tgt = target.copy()
    tgt.index = _normalized_key_index(target, key_columns)
    _require_unique_index(src, "source", key_columns)
    _require_unique_index(tgt, "target", key_columns)

    src_keys, tgt_keys = set(src.index), set(tgt.index)
    only_in_source = src_keys - tgt_keys
    only_in_target = tgt_keys - src_keys
    common_keys = src_keys & tgt_keys

    missing_in_target, truncated_a = _sample_missing_rows(src, only_in_source, key_columns)
    missing_in_source, truncated_b = _sample_missing_rows(tgt, only_in_target, key_columns)

    mismatches: list[ColumnMismatch] = []
    mismatched_row_count = 0
    mismatched_cell_count = 0
    truncated_c = False

    if common_keys:
        ordered_common = sorted(common_keys, key=str)
        mismatches, mismatched_cell_count, mismatched_row_count, truncated_c = _diff_common_rows(
            src.loc[ordered_common], tgt.loc[ordered_common], cols, key_columns, numeric_tolerance
        )

    summary = ComparisonSummary(
        source_row_count=len(source),
        target_row_count=len(target),
        matched_row_count=len(common_keys) - mismatched_row_count,
        missing_in_target_count=len(only_in_source),
        missing_in_source_count=len(only_in_target),
        mismatched_row_count=mismatched_row_count,
        mismatched_cell_count=mismatched_cell_count,
    )

    return ComparisonOutcome(
        summary=summary,
        missing_in_target=missing_in_target,
        missing_in_source=missing_in_source,
        mismatches=mismatches,
        truncated=truncated_a or truncated_b or truncated_c,
    )
