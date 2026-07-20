# SPDX-FileCopyrightText: 2026 James G Willmore
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from decimal import Decimal

import pandas as pd
import pytest

from pydoublecross.exceptions import ValidationEngineError
from pydoublecross.validation.comparators import compare_dataframes


def test_identical_frames_fully_match() -> None:
    source = pd.DataFrame({"id": [1, 2, 3], "name": ["a", "b", "c"]})
    target = source.copy()
    outcome = compare_dataframes(source, target, key_columns=["id"])
    assert outcome.summary.rows_fully_match
    assert outcome.summary.matched_row_count == 3
    assert outcome.mismatches == []


def test_missing_rows_detected_both_directions() -> None:
    source = pd.DataFrame({"id": [1, 2, 3], "name": ["a", "b", "c"]})
    target = pd.DataFrame({"id": [2, 3, 4], "name": ["b", "c", "d"]})
    outcome = compare_dataframes(source, target, key_columns=["id"])
    assert outcome.summary.missing_in_target_count == 1
    assert outcome.summary.missing_in_source_count == 1
    assert outcome.missing_in_target == [{"id": 1}]
    assert outcome.missing_in_source == [{"id": 4}]


def test_value_mismatch_detected() -> None:
    source = pd.DataFrame({"id": [1, 2], "email": ["a@x.com", "b@x.com"]})
    target = pd.DataFrame({"id": [1, 2], "email": ["a@x.com", "WRONG@x.com"]})
    outcome = compare_dataframes(source, target, key_columns=["id"])
    assert outcome.summary.mismatched_row_count == 1
    assert outcome.summary.mismatched_cell_count == 1
    assert len(outcome.mismatches) == 1
    m = outcome.mismatches[0]
    assert m.column == "email"
    assert m.source_value == "b@x.com"
    assert m.target_value == "WRONG@x.com"


def test_value_whitespace_padding_is_not_a_mismatch() -> None:
    # e.g. a fixed-width CHAR(20) column padded with trailing spaces on one side.
    source = pd.DataFrame({"id": [1], "role": ["producer"]})
    target = pd.DataFrame({"id": [1], "role": ["producer   "]})
    outcome = compare_dataframes(source, target, key_columns=["id"])
    assert outcome.summary.mismatched_cell_count == 0


def test_value_case_difference_is_still_a_mismatch() -> None:
    # Whitespace is forgiven, but this must not become a blanket "loose" comparison.
    source = pd.DataFrame({"id": [1], "role": ["producer"]})
    target = pd.DataFrame({"id": [1], "role": ["Producer"]})
    outcome = compare_dataframes(source, target, key_columns=["id"])
    assert outcome.summary.mismatched_cell_count == 1


def test_numeric_tolerance_suppresses_small_diffs() -> None:
    source = pd.DataFrame({"id": [1], "amount": [10.001]})
    target = pd.DataFrame({"id": [1], "amount": [10.002]})
    outcome = compare_dataframes(source, target, key_columns=["id"], numeric_tolerance=0.01)
    assert outcome.summary.mismatched_cell_count == 0

    outcome_strict = compare_dataframes(source, target, key_columns=["id"], numeric_tolerance=0.0)
    assert outcome_strict.summary.mismatched_cell_count == 1


def test_null_vs_value_is_a_mismatch() -> None:
    source = pd.DataFrame({"id": [1], "note": [None]})
    target = pd.DataFrame({"id": [1], "note": ["hello"]})
    outcome = compare_dataframes(source, target, key_columns=["id"])
    assert outcome.summary.mismatched_cell_count == 1


def test_both_null_is_not_a_mismatch() -> None:
    source = pd.DataFrame({"id": [1], "note": [None]})
    target = pd.DataFrame({"id": [1], "note": [None]})
    outcome = compare_dataframes(source, target, key_columns=["id"])
    assert outcome.summary.mismatched_cell_count == 0


def test_ignore_columns_excluded_from_default_comparison() -> None:
    source = pd.DataFrame({"id": [1], "name": ["a"], "updated_at": ["2026-01-01"]})
    target = pd.DataFrame({"id": [1], "name": ["a"], "updated_at": ["2026-06-01"]})
    outcome = compare_dataframes(source, target, key_columns=["id"], ignore_columns=["updated_at"])
    assert outcome.summary.mismatched_cell_count == 0


def test_explicit_compare_columns_missing_raises() -> None:
    source = pd.DataFrame({"id": [1], "name": ["a"]})
    target = pd.DataFrame({"id": [1], "name": ["a"]})
    with pytest.raises(ValidationEngineError, match="compare_columns"):
        compare_dataframes(source, target, key_columns=["id"], compare_columns=["does_not_exist"])


def test_duplicate_key_raises() -> None:
    source = pd.DataFrame({"id": [1, 1], "name": ["a", "b"]})
    target = pd.DataFrame({"id": [1], "name": ["a"]})
    with pytest.raises(ValidationEngineError, match="not unique"):
        compare_dataframes(source, target, key_columns=["id"])


def test_missing_key_column_raises() -> None:
    source = pd.DataFrame({"name": ["a"]})
    target = pd.DataFrame({"name": ["a"]})
    with pytest.raises(ValidationEngineError, match="key_columns"):
        compare_dataframes(source, target, key_columns=["id"])


def test_composite_key_columns() -> None:
    source = pd.DataFrame({"a": [1, 1], "b": [1, 2], "v": [10, 20]})
    target = pd.DataFrame({"a": [1, 1], "b": [1, 2], "v": [10, 99]})
    outcome = compare_dataframes(source, target, key_columns=["a", "b"])
    assert outcome.summary.mismatched_row_count == 1
    assert outcome.mismatches[0].key == {"a": 1, "b": 2}


def test_key_matches_across_int_and_string_dtype() -> None:
    # e.g. source driver returns an INTEGER id as int64, target returns a
    # VARCHAR id as str - same logical key, different Python types.
    source = pd.DataFrame({"id": [1, 2, 3], "name": ["a", "b", "c"]})
    target = pd.DataFrame({"id": ["1", "2", "3"], "name": ["a", "b", "c"]})
    outcome = compare_dataframes(source, target, key_columns=["id"])
    assert outcome.summary.rows_fully_match
    assert outcome.summary.missing_in_target_count == 0
    assert outcome.summary.missing_in_source_count == 0


def test_key_matches_across_decimal_and_int_dtype() -> None:
    # e.g. an Oracle NUMBER column comes back as decimal.Decimal via the driver.
    source = pd.DataFrame({"id": [1, 2], "name": ["a", "b"]})
    target = pd.DataFrame({"id": [Decimal("1"), Decimal("2.00")], "name": ["a", "b"]})
    outcome = compare_dataframes(source, target, key_columns=["id"])
    assert outcome.summary.rows_fully_match


def test_key_matches_with_whitespace_padding() -> None:
    # e.g. a fixed-width CHAR(10) column padded with trailing spaces on one side.
    source = pd.DataFrame({"id": ["ABC123"], "name": ["a"]})
    target = pd.DataFrame({"id": ["ABC123   "], "name": ["a"]})
    outcome = compare_dataframes(source, target, key_columns=["id"])
    assert outcome.summary.rows_fully_match


def test_key_mismatch_still_detected_when_genuinely_different() -> None:
    # Type-normalization must not hide real differences.
    source = pd.DataFrame({"id": [1, 2], "name": ["a", "b"]})
    target = pd.DataFrame({"id": ["1", "3"], "name": ["a", "c"]})
    outcome = compare_dataframes(source, target, key_columns=["id"])
    assert outcome.summary.missing_in_target_count == 1  # id 2
    assert outcome.summary.missing_in_source_count == 1  # id 3
    assert outcome.missing_in_target == [{"id": 2}]
    assert outcome.missing_in_source == [{"id": "3"}]


def test_key_display_value_is_the_original_not_the_normalized_form() -> None:
    # Matching is normalized, but reported key/value samples must show what was
    # actually fetched from each side, so users can see the real discrepancy.
    source = pd.DataFrame({"id": [1], "email": ["a@x.com"]})
    target = pd.DataFrame({"id": ["1"], "email": ["WRONG@x.com"]})
    outcome = compare_dataframes(source, target, key_columns=["id"])
    assert outcome.summary.mismatched_cell_count == 1
    m = outcome.mismatches[0]
    assert m.key == {"id": 1}  # source's own representation
    assert m.source_value == "a@x.com"
    assert m.target_value == "WRONG@x.com"
