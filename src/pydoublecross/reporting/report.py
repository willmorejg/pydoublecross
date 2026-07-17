# SPDX-FileCopyrightText: 2026 James G Willmore
# SPDX-License-Identifier: Apache-2.0

"""Turn a `ValidationRunResult` into flat, tabular data shared by all exporters."""

from __future__ import annotations

from typing import Any

from pydoublecross.validation.results import ValidationRunResult


def summary_rows(result: ValidationRunResult) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {"metric": "item_name", "value": result.item_name},
        {"metric": "run_id", "value": result.run_id},
        {"metric": "status", "value": result.status.value},
        {"metric": "started_at", "value": result.started_at.isoformat()},
        {"metric": "finished_at", "value": result.finished_at.isoformat()},
        {"metric": "source_cache_hit", "value": result.source_cache_hit},
        {"metric": "target_cache_hit", "value": result.target_cache_hit},
        {"metric": "truncated_sample", "value": result.truncated},
    ]
    if result.error:
        rows.append({"metric": "error", "value": result.error})
    if result.summary:
        s = result.summary
        rows.extend(
            [
                {"metric": "source_row_count", "value": s.source_row_count},
                {"metric": "target_row_count", "value": s.target_row_count},
                {"metric": "matched_row_count", "value": s.matched_row_count},
                {"metric": "missing_in_target_count", "value": s.missing_in_target_count},
                {"metric": "missing_in_source_count", "value": s.missing_in_source_count},
                {"metric": "mismatched_row_count", "value": s.mismatched_row_count},
                {"metric": "mismatched_cell_count", "value": s.mismatched_cell_count},
            ]
        )
    return rows


def mismatch_rows(result: ValidationRunResult) -> list[dict[str, Any]]:
    rows = []
    for m in result.mismatches:
        row = {f"key.{k}": v for k, v in m.key.items()}
        row.update(
            {"column": m.column, "source_value": m.source_value, "target_value": m.target_value}
        )
        rows.append(row)
    return rows


def ge_result_rows(result: ValidationRunResult) -> list[dict[str, Any]]:
    return [
        {
            "role": r.role,
            "success": r.success,
            "expectations_evaluated": r.expectations_evaluated,
            "expectations_failed": r.expectations_failed,
            "failed_expectation_types": ", ".join(r.failed_expectation_types),
        }
        for r in result.ge_results
    ]
