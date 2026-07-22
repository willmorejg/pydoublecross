# SPDX-FileCopyrightText: 2026 James G Willmore
# SPDX-License-Identifier: Apache-2.0

"""Validation engine: caching-aware fetch, per-side engine checks, and comparison."""

from pydoublecross.validation.comparators import compare_dataframes
from pydoublecross.validation.engine import CacheMode, ValidationEngine, resolve_cache_mode
from pydoublecross.validation.results import (
    ColumnMismatch,
    ComparisonOutcome,
    ComparisonSummary,
    EngineCheckResult,
    RunStatus,
    ValidationRunResult,
)

__all__ = [
    "CacheMode",
    "ColumnMismatch",
    "ComparisonOutcome",
    "ComparisonSummary",
    "EngineCheckResult",
    "RunStatus",
    "ValidationEngine",
    "ValidationRunResult",
    "compare_dataframes",
    "resolve_cache_mode",
]
