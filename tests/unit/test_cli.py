# SPDX-FileCopyrightText: 2026 James G Willmore
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from pydoublecross.cli.main import app

cli_runner = CliRunner()


def test_validate_config(config_path: Path) -> None:
    result = cli_runner.invoke(app, ["validate-config", "-c", str(config_path)])
    assert result.exit_code == 0
    assert "valid" in result.stdout.lower()


def test_validate_config_missing_file(tmp_path: Path) -> None:
    result = cli_runner.invoke(app, ["validate-config", "-c", str(tmp_path / "nope.yaml")])
    assert result.exit_code == 1


def test_list_items(config_path: Path) -> None:
    result = cli_runner.invoke(app, ["list", "-c", str(config_path)])
    assert result.exit_code == 0
    assert "customer_check" in result.stdout


def test_run_reports_failure_exit_code(config_path: Path) -> None:
    result = cli_runner.invoke(app, ["run", "customer_check", "-c", str(config_path)])
    assert result.exit_code == 1  # the fixture data has intentional mismatches
    assert "customer_check" in result.stdout


def test_run_with_export(config_path: Path, tmp_path: Path) -> None:
    output = tmp_path / "out_report"
    result = cli_runner.invoke(
        app,
        [
            "run",
            "customer_check",
            "-c",
            str(config_path),
            "--export",
            "excel",
            "--output",
            str(output),
        ],
    )
    assert result.exit_code == 1
    assert output.with_suffix(".xlsx").is_file()


def test_test_connection_success(config_path: Path) -> None:
    result = cli_runner.invoke(app, ["test-connection", "src", "-c", str(config_path)])
    assert result.exit_code == 0
    assert "OK" in result.stdout


def test_test_connection_unknown_datasource(config_path: Path) -> None:
    result = cli_runner.invoke(app, ["test-connection", "does_not_exist", "-c", str(config_path)])
    assert result.exit_code == 1


def test_cache_clear(config_path: Path) -> None:
    cli_runner.invoke(app, ["run", "customer_check", "-c", str(config_path)])
    result = cli_runner.invoke(app, ["cache", "clear", "-c", str(config_path)])
    assert result.exit_code == 0
    assert "Removed" in result.stdout
