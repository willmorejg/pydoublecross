# SPDX-FileCopyrightText: 2026 James G Willmore
# SPDX-License-Identifier: Apache-2.0

"""End-to-end run through `ValidationRunner` against two real SQLite databases."""

from __future__ import annotations

from pathlib import Path

import openpyxl

from pydoublecross.core.runner import ValidationRunner
from pydoublecross.validation.results import RunStatus


def test_full_run_detects_known_mismatches(runner: ValidationRunner) -> None:
    result = runner.run("customer_check")

    assert result.status == RunStatus.FAILED
    assert result.error is None
    assert result.summary is not None
    assert result.summary.source_row_count == 3
    assert result.summary.target_row_count == 3
    assert result.summary.missing_in_target_count == 1  # customer 3
    assert result.summary.missing_in_source_count == 1  # customer 4
    assert result.summary.mismatched_row_count == 1  # customer 2's email
    assert all(er.success for er in result.engine_results)


def test_source_cache_hit_on_second_run(runner: ValidationRunner) -> None:
    first = runner.run("customer_check")
    second = runner.run("customer_check")
    assert first.source_cache_hit is False
    assert second.source_cache_hit is True
    # target caching is disabled in the fixture config
    assert second.target_cache_hit is False


def test_refresh_cache_forces_a_new_fetch(runner: ValidationRunner) -> None:
    runner.run("customer_check")
    refreshed = runner.run("customer_check", cache_mode="refresh")
    assert refreshed.source_cache_hit is False


def test_bypass_cache_never_reads_or_reports_a_hit(runner: ValidationRunner) -> None:
    runner.run("customer_check")
    bypassed = runner.run("customer_check", cache_mode="bypass")
    assert bypassed.source_cache_hit is False


def test_run_persists_and_is_retrievable_from_history(runner: ValidationRunner) -> None:
    result = runner.run("customer_check")
    fetched = runner.get_result("customer_check", result.run_id)
    assert fetched is not None
    assert fetched.run_id == result.run_id

    history = runner.history("customer_check")
    assert len(history) == 1
    assert history[0].run_id == result.run_id


def test_run_all_runs_every_item(runner: ValidationRunner) -> None:
    results = runner.run_all()
    assert {r.item_name for r in results} == {
        "customer_check",
        "customer_check_pandera",
        "customer_check_both",
    }


def test_pandera_engine_choice_runs_only_pandera(runner: ValidationRunner) -> None:
    result = runner.run("customer_check_pandera")
    assert {er.engine for er in result.engine_results} == {"pandera"}
    assert len(result.engine_results) == 2  # source + target
    assert all(er.success for er in result.engine_results)


def test_both_engine_choice_runs_both(runner: ValidationRunner) -> None:
    result = runner.run("customer_check_both")
    assert {er.engine for er in result.engine_results} == {"great_expectations", "pandera"}
    assert len(result.engine_results) == 4  # 2 engines x source/target
    assert all(er.success for er in result.engine_results)


def test_export_to_excel(runner: ValidationRunner, tmp_path: Path) -> None:
    result = runner.run("customer_check")
    destination = tmp_path / "export"
    path = runner.export(result, "excel", destination)
    assert path.is_file()
    wb = openpyxl.load_workbook(path)
    assert "Summary" in wb.sheetnames


def test_test_connection(runner: ValidationRunner) -> None:
    assert runner.test_connection("src") is True


def test_clear_cache_removes_entries(runner: ValidationRunner) -> None:
    runner.run("customer_check")
    removed = runner.clear_cache("src")
    assert removed > 0
    after = runner.run("customer_check")
    assert after.source_cache_hit is False
