# SPDX-FileCopyrightText: 2026 James G Willmore
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import datetime

from bump_version import next_calver


def test_same_month_increments_micro() -> None:
    assert next_calver("2026.7.1", datetime.date(2026, 7, 15)) == "2026.7.2"
    assert next_calver("2026.7.9", datetime.date(2026, 7, 20)) == "2026.7.10"


def test_month_rollover_resets_micro_to_one() -> None:
    assert next_calver("2026.7.9", datetime.date(2026, 8, 1)) == "2026.8.1"


def test_year_rollover_resets_micro_to_one() -> None:
    assert next_calver("2026.12.5", datetime.date(2027, 1, 1)) == "2027.1.1"


def test_existing_local_version_suffix_is_ignored() -> None:
    assert next_calver("2026.7.4+abc1234", datetime.date(2026, 7, 20)) == "2026.7.5"


def test_malformed_current_version_resets_to_one() -> None:
    assert next_calver("not-a-version", datetime.date(2026, 7, 20)) == "2026.7.1"
