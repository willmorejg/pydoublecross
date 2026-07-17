# SPDX-FileCopyrightText: 2026 James G Willmore
# SPDX-License-Identifier: Apache-2.0

"""pyDoubleCross command-line interface."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from pydoublecross import __version__
from pydoublecross.core.runner import ValidationRunner
from pydoublecross.exceptions import PyDoubleCrossError
from pydoublecross.logging_conf import configure_logging
from pydoublecross.validation.engine import CacheMode
from pydoublecross.validation.results import RunStatus

app = typer.Typer(
    name="pydoublecross",
    help="Validate data consistency between a source and a target data source.",
    no_args_is_help=True,
)
cache_app = typer.Typer(help="Inspect and clear cached query results.")
app.add_typer(cache_app, name="cache")

console = Console()

DEFAULT_CONFIG = Path("config/example.yaml")

ConfigOption = Annotated[
    Path,
    typer.Option("--config", "-c", help="Path to the YAML configuration file."),
]


def _cache_mode(no_cache: bool, refresh_cache: bool) -> CacheMode:
    if refresh_cache:
        return "refresh"
    if no_cache:
        return "bypass"
    return "default"


def _load_runner(config: Path) -> ValidationRunner:
    configure_logging()
    try:
        return ValidationRunner.from_config_path(config)
    except PyDoubleCrossError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc


def _print_result(result) -> None:
    color = {"passed": "green", "failed": "red", "error": "red"}[result.status.value]
    console.print(
        f"[bold {color}]{result.status.value.upper()}[/bold {color}] — {result.item_name} (run {result.run_id})"
    )

    if result.error:
        console.print(f"[red]{result.error}[/red]")
        return

    table = Table(show_header=False)
    s = result.summary
    table.add_row("Source rows", str(s.source_row_count))
    table.add_row("Target rows", str(s.target_row_count))
    table.add_row("Matched rows", str(s.matched_row_count))
    table.add_row("Missing in target", str(s.missing_in_target_count))
    table.add_row("Missing in source", str(s.missing_in_source_count))
    table.add_row("Mismatched rows", str(s.mismatched_row_count))
    table.add_row("Mismatched cells", str(s.mismatched_cell_count))
    table.add_row("Source cache hit", str(result.source_cache_hit))
    table.add_row("Target cache hit", str(result.target_cache_hit))
    console.print(table)

    for ge in result.ge_results:
        status = "OK" if ge.success else "FAILED"
        console.print(
            f"  GE ({ge.role}): {status} "
            f"({ge.expectations_evaluated - ge.expectations_failed}/{ge.expectations_evaluated} passed)"
        )


@app.command()
def version() -> None:
    """Print the installed version."""
    console.print(__version__)


@app.command("validate-config")
def validate_config(config: ConfigOption = DEFAULT_CONFIG) -> None:
    """Load and validate the configuration file without running anything."""
    _load_runner(config)
    console.print("[green]Configuration is valid.[/green]")


@app.command("list")
def list_items(config: ConfigOption = DEFAULT_CONFIG) -> None:
    """List configured validation items."""
    runner = _load_runner(config)
    table = Table("Name", "Description", "Source", "Target")
    for item in runner.list_items():
        table.add_row(
            item["name"],
            item["description"] or "",
            item["source_data_source"],
            item["target_data_source"],
        )
    console.print(table)


@app.command()
def run(
    item_name: Annotated[str, typer.Argument(help="Name of the validation item to run.")],
    config: ConfigOption = DEFAULT_CONFIG,
    no_cache: Annotated[bool, typer.Option(help="Bypass the cache for this run.")] = False,
    refresh_cache: Annotated[
        bool, typer.Option(help="Force-refresh the cache for this run.")
    ] = False,
    export: Annotated[str | None, typer.Option(help="Export format, e.g. 'excel'.")] = None,
    output: Annotated[Path | None, typer.Option(help="Output path for the export.")] = None,
) -> None:
    """Run one validation item."""
    runner = _load_runner(config)
    cache_mode = _cache_mode(no_cache, refresh_cache)
    try:
        result = runner.run(item_name, cache_mode=cache_mode)
    except PyDoubleCrossError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    _print_result(result)

    if export:
        destination = output or Path(f"{item_name}_{result.run_id}")
        path = runner.export(result, export, destination)
        console.print(f"Report written to [cyan]{path}[/cyan]")

    if result.status != RunStatus.PASSED:
        raise typer.Exit(code=1)


@app.command("run-all")
def run_all(
    config: ConfigOption = DEFAULT_CONFIG,
    no_cache: Annotated[bool, typer.Option(help="Bypass the cache for this run.")] = False,
    refresh_cache: Annotated[
        bool, typer.Option(help="Force-refresh the cache for this run.")
    ] = False,
) -> None:
    """Run every configured validation item."""
    runner = _load_runner(config)
    cache_mode = _cache_mode(no_cache, refresh_cache)
    results = runner.run_all(cache_mode=cache_mode)
    failures = 0
    for result in results:
        _print_result(result)
        if result.status != RunStatus.PASSED:
            failures += 1
    if failures:
        raise typer.Exit(code=1)


@app.command("test-connection")
def test_connection(
    data_source: str,
    config: ConfigOption = DEFAULT_CONFIG,
) -> None:
    """Test connectivity to a named data source."""
    runner = _load_runner(config)
    try:
        runner.test_connection(data_source)
    except PyDoubleCrossError as exc:
        console.print(f"[bold red]FAILED:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print(f"[green]OK[/green] — connected to '{data_source}'")


@cache_app.command("clear")
def cache_clear(
    config: ConfigOption = DEFAULT_CONFIG,
    data_source: Annotated[
        str | None, typer.Option(help="Only clear this data source's cache.")
    ] = None,
) -> None:
    """Clear cached query results."""
    runner = _load_runner(config)
    removed = runner.clear_cache(data_source)
    console.print(f"Removed {removed} cache file(s).")


@app.command()
def serve(
    config: ConfigOption = DEFAULT_CONFIG,
    host: Annotated[str | None, typer.Option(help="Override the configured host.")] = None,
    port: Annotated[int | None, typer.Option(help="Override the configured port.")] = None,
    reload: Annotated[bool, typer.Option(help="Enable auto-reload (development only).")] = False,
) -> None:
    """Serve the REST API and web UI together."""
    import os

    import uvicorn

    runner = _load_runner(config)
    bind_host = host or runner.config.server.host
    bind_port = port or runner.config.server.port

    os.environ["PYDOUBLECROSS_CONFIG_PATH"] = str(config)
    console.print(f"Serving on http://{bind_host}:{bind_port} (config: {config})")
    uvicorn.run(
        "pydoublecross.web.app:build_app_from_env",
        host=bind_host,
        port=bind_port,
        reload=reload,
        factory=True,
    )


if __name__ == "__main__":
    app()
