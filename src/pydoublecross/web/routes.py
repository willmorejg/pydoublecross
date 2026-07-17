# SPDX-FileCopyrightText: 2026 James G Willmore
# SPDX-License-Identifier: Apache-2.0

"""Server-rendered page routes for the web UI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from pydoublecross.api.deps import apply_config_change
from pydoublecross.config.models import (
    CacheDefaults,
    CacheOverride,
    DataSourceConfig,
    DataSourceRef,
    ExpectationToggles,
    ValidationItemConfig,
)
from pydoublecross.core.runner import ValidationRunner
from pydoublecross.exceptions import PyDoubleCrossError
from pydoublecross.validation.results import RunStatus

router = APIRouter()

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _runner(request: Request) -> ValidationRunner:
    return request.app.state.runner


def _split_list(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def _parse_extra_params(raw: str) -> dict[str, str]:
    params: dict[str, str] = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line or "=" not in line:
            continue
        key, _, value = line.partition("=")
        params[key.strip()] = value.strip()
    return params


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request) -> HTMLResponse:
    runner = _runner(request)
    items = []
    for item in runner.list_items():
        last_runs = runner.history(item["name"], limit=1)
        items.append({**item, "last_run": last_runs[0] if last_runs else None})
    return templates.TemplateResponse(
        request, "dashboard.html", {"items": items, "RunStatus": RunStatus}
    )


# --- Data sources ---------------------------------------------------------


@router.get("/datasources", response_class=HTMLResponse)
def datasource_list(request: Request) -> HTMLResponse:
    runner = _runner(request)
    return templates.TemplateResponse(
        request, "datasources.html", {"data_sources": runner.config.data_sources}
    )


@router.get("/datasources/new", response_class=HTMLResponse)
def datasource_new_form(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "datasource_form.html", {"name": None, "ds": None})


@router.get("/datasources/{name}/edit", response_class=HTMLResponse)
def datasource_edit_form(request: Request, name: str) -> HTMLResponse:
    runner = _runner(request)
    ds = runner.config.data_sources.get(name)
    return templates.TemplateResponse(request, "datasource_form.html", {"name": name, "ds": ds})


def _datasource_from_form(form: Any) -> DataSourceConfig:
    return DataSourceConfig(
        type=form["type"],
        host=form.get("host") or None,
        port=int(form["port"]) if form.get("port") else None,
        database=form.get("database") or None,
        username=form.get("username") or None,
        password=form.get("password") or None,
        path=form.get("path") or None,
        driver=form.get("driver") or None,
        extra_params=_parse_extra_params(str(form.get("extra_params", ""))),
        cache=CacheDefaults(
            enabled=form.get("cache_enabled") == "on",
            ttl_seconds=int(form.get("cache_ttl_seconds") or 3600),
        ),
    )


def _save_datasource(runner: ValidationRunner, name: str, form: Any) -> None:
    config = _datasource_from_form(form)
    if not form.get("password"):
        existing = runner.config.data_sources.get(name)
        if existing and existing.password:
            config.password = existing.password

    def mutate(data: dict[str, Any]) -> None:
        data["data_sources"][name] = config.model_dump(mode="json")

    apply_config_change(runner, mutate)


@router.post("/datasources")
async def datasource_create(request: Request) -> RedirectResponse:
    form = await request.form()
    _save_datasource(_runner(request), str(form["name"]), form)
    return RedirectResponse(url="/datasources", status_code=303)


@router.post("/datasources/{name}")
async def datasource_update(request: Request, name: str) -> RedirectResponse:
    form = await request.form()
    _save_datasource(_runner(request), name, form)
    return RedirectResponse(url="/datasources", status_code=303)


@router.post("/datasources/{name}/delete")
def datasource_delete(request: Request, name: str) -> RedirectResponse:
    runner = _runner(request)

    def mutate(data: dict[str, Any]) -> None:
        data["data_sources"].pop(name, None)

    apply_config_change(runner, mutate)
    return RedirectResponse(url="/datasources", status_code=303)


# --- Validation items -------------------------------------------------------


def _ref_from_form(prefix: str, form: dict[str, Any]) -> DataSourceRef:
    return DataSourceRef(
        data_source=form[f"{prefix}_data_source"],
        sql=form.get(f"{prefix}_sql") or None,
        table=form.get(f"{prefix}_table") or None,
        cache=CacheOverride(
            enabled=(
                None
                if form.get(f"{prefix}_cache_enabled") == "inherit"
                else form.get(f"{prefix}_cache_enabled") == "on"
            ),
            force_refresh=form.get(f"{prefix}_force_refresh") == "on",
        ),
    )


def _validation_from_form(form: dict[str, Any]) -> ValidationItemConfig:
    return ValidationItemConfig(
        description=form.get("description") or None,
        source=_ref_from_form("source", form),
        target=_ref_from_form("target", form),
        key_columns=_split_list(str(form.get("key_columns", ""))),
        compare_columns=(
            _split_list(str(form["compare_columns"])) if form.get("compare_columns") else None
        ),
        ignore_columns=_split_list(str(form.get("ignore_columns", ""))),
        numeric_tolerance=float(form.get("numeric_tolerance") or 0.0),
        expectations=ExpectationToggles(
            row_count_match=form.get("row_count_match") == "on",
            schema_match=form.get("schema_match") == "on",
            null_checks=form.get("null_checks") == "on",
        ),
    )


def _save_validation(runner: ValidationRunner, name: str, form: dict[str, Any]) -> None:
    item = _validation_from_form(form)

    def mutate(data: dict[str, Any]) -> None:
        data["validations"][name] = item.model_dump(mode="json")

    apply_config_change(runner, mutate)


@router.get("/validations/new", response_class=HTMLResponse)
def validation_new_form(request: Request) -> HTMLResponse:
    runner = _runner(request)
    return templates.TemplateResponse(
        request,
        "validation_form.html",
        {"name": None, "item": None, "data_sources": runner.config.data_sources},
    )


@router.get("/validations/{name}/edit", response_class=HTMLResponse)
def validation_edit_form(request: Request, name: str) -> HTMLResponse:
    runner = _runner(request)
    item = runner.config.validations.get(name)
    return templates.TemplateResponse(
        request,
        "validation_form.html",
        {"name": name, "item": item, "data_sources": runner.config.data_sources},
    )


@router.post("/validations")
async def validation_create(request: Request) -> RedirectResponse:
    form = dict(await request.form())
    _save_validation(_runner(request), str(form["name"]), form)
    return RedirectResponse(url="/", status_code=303)


@router.post("/validations/{name}")
async def validation_update(request: Request, name: str) -> RedirectResponse:
    form = dict(await request.form())
    _save_validation(_runner(request), name, form)
    return RedirectResponse(url="/", status_code=303)


@router.post("/validations/{name}/delete")
def validation_delete(request: Request, name: str) -> RedirectResponse:
    runner = _runner(request)

    def mutate(data: dict[str, Any]) -> None:
        data["validations"].pop(name, None)

    apply_config_change(runner, mutate)
    return RedirectResponse(url="/", status_code=303)


@router.post("/validations/{name}/run")
def validation_run(request: Request, name: str):
    runner = _runner(request)
    try:
        result = runner.run(name)
    except PyDoubleCrossError as exc:
        items = [{**i, "last_run": None} for i in runner.list_items()]
        return templates.TemplateResponse(
            request,
            "dashboard.html",
            {"items": items, "RunStatus": RunStatus, "error": str(exc)},
            status_code=400,
        )
    return RedirectResponse(url=f"/validations/{name}/results/{result.run_id}", status_code=303)


@router.get("/validations/{name}/results/{run_id}", response_class=HTMLResponse)
def validation_result(request: Request, name: str, run_id: str) -> HTMLResponse:
    runner = _runner(request)
    result = runner.get_result(name, run_id)
    return templates.TemplateResponse(
        request, "validation_result.html", {"result": result, "item_name": name}
    )


@router.get("/validations/{name}/results", response_class=HTMLResponse)
def validation_history(request: Request, name: str) -> HTMLResponse:
    runner = _runner(request)
    results = runner.history(name)
    return templates.TemplateResponse(
        request, "validation_history.html", {"item_name": name, "results": results}
    )
