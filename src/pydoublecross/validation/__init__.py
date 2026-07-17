# SPDX-FileCopyrightText: 2026 James G Willmore
# SPDX-License-Identifier: Apache-2.0

"""Validation engine: caching-aware fetch, Great Expectations checks, and comparison."""

from pydoublecross.validation.comparators import compare_dataframes
from pydoublecross.validation.engine import CacheMode, ValidationEngine
from pydoublecross.validation.results import (
    ColumnMismatch,
    ComparisonOutcome,
    ComparisonSummary,
    GESideResult,
    RunStatus,
    ValidationRunResult,
)

__all__ = [
    "CacheMode",
    "ColumnMismatch",
    "ComparisonOutcome",
    "ComparisonSummary",
    "GESideResult",
    "RunStatus",
    "ValidationEngine",
    "ValidationRunResult",
    "compare_dataframes",
]
