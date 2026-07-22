# SPDX-FileCopyrightText: 2026 James G Willmore
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import pandas as pd

from pydoublecross.config.models import ExpectationToggles
from pydoublecross.validation.pandera_suite import run_side_checks


def test_passes_clean_frame() -> None:
    frame = pd.DataFrame({"id": [1, 2, 3], "name": ["a", "b", "c"]})
    result = run_side_checks(frame, "source", ExpectationToggles())
    assert result.engine == "pandera"
    assert result.role == "source"
    assert result.success is True
    assert result.checks_failed == 0
    assert result.checks_evaluated > 0


def test_null_check_fails_on_unexpected_null() -> None:
    frame = pd.DataFrame({"id": [1, 2], "name": ["a", None]})
    result = run_side_checks(frame, "source", ExpectationToggles())
    assert result.success is False
    assert result.checks_failed >= 1
    assert "not_nullable" in result.failed_check_names


def test_entirely_null_column_is_skipped_not_flagged() -> None:
    frame = pd.DataFrame({"id": [1, 2], "note": [None, None]})
    result = run_side_checks(frame, "source", ExpectationToggles())
    assert result.success is True


def test_row_count_check_fails_on_empty_frame() -> None:
    frame = pd.DataFrame({"id": pd.Series([], dtype="int64")})
    result = run_side_checks(frame, "target", ExpectationToggles())
    assert result.success is False
    assert "row_count_positive" in result.failed_check_names


def test_toggles_off_disable_their_checks() -> None:
    frame = pd.DataFrame({"id": [1], "name": [None]})
    toggles = ExpectationToggles(row_count_match=False, schema_match=False, null_checks=False)
    result = run_side_checks(frame, "source", toggles)
    assert result.success is True
    assert result.checks_evaluated == 0
