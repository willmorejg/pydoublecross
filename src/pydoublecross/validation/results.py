# SPDX-FileCopyrightText: 2026 James G Willmore
# SPDX-License-Identifier: Apache-2.0

"""Pydantic models describing the outcome of one validation run."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field

MAX_SAMPLE_ROWS = 200


class RunStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"


class ColumnMismatch(BaseModel):
    key: dict[str, Any]
    column: str
    source_value: Any
    target_value: Any


class GESideResult(BaseModel):
    role: Literal["source", "target"]
    success: bool
    expectations_evaluated: int
    expectations_failed: int
    failed_expectation_types: list[str] = Field(default_factory=list)


class ComparisonSummary(BaseModel):
    source_row_count: int
    target_row_count: int
    matched_row_count: int
    missing_in_target_count: int
    missing_in_source_count: int
    mismatched_row_count: int
    mismatched_cell_count: int

    @property
    def rows_fully_match(self) -> bool:
        return (
            self.missing_in_target_count == 0
            and self.missing_in_source_count == 0
            and self.mismatched_row_count == 0
        )


class ComparisonOutcome(BaseModel):
    summary: ComparisonSummary
    missing_in_target: list[dict[str, Any]] = Field(default_factory=list)
    missing_in_source: list[dict[str, Any]] = Field(default_factory=list)
    mismatches: list[ColumnMismatch] = Field(default_factory=list)
    truncated: bool = False


class ValidationRunResult(BaseModel):
    item_name: str
    run_id: str
    started_at: datetime
    finished_at: datetime
    status: RunStatus
    source_cache_hit: bool = False
    target_cache_hit: bool = False
    summary: ComparisonSummary | None = None
    missing_in_target: list[dict[str, Any]] = Field(default_factory=list)
    missing_in_source: list[dict[str, Any]] = Field(default_factory=list)
    mismatches: list[ColumnMismatch] = Field(default_factory=list)
    truncated: bool = False
    ge_results: list[GESideResult] = Field(default_factory=list)
    error: str | None = None
