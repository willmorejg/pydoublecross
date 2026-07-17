# SPDX-FileCopyrightText: 2026 James G Willmore
# SPDX-License-Identifier: Apache-2.0

"""CRUD and connection testing for named data sources."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException

from pydoublecross.api.deps import apply_config_change, get_runner
from pydoublecross.api.schemas import ConnectionTestResult, DataSourceSummary
from pydoublecross.config.models import DataSourceConfig
from pydoublecross.core.runner import ValidationRunner
from pydoublecross.exceptions import DataSourceError

router = APIRouter(prefix="/api/datasources", tags=["datasources"])


def _public(name: str, config: DataSourceConfig) -> dict[str, Any]:
    data = config.model_dump(mode="json")
    if data.get("password"):
        data["password"] = "***"
    if data.get("url"):
        data["url"] = "***"  # may embed credentials, e.g. postgresql://user:pass@host/db
    data["name"] = name
    return data


@router.get("", response_model=list[DataSourceSummary])
def list_datasources(runner: Annotated[ValidationRunner, Depends(get_runner)]):
    return [
        DataSourceSummary(
            name=name, type=ds.type, cache_enabled=ds.cache.enabled, uses_url=bool(ds.url)
        )
        for name, ds in runner.config.data_sources.items()
    ]


@router.get("/{name}")
def get_datasource(name: str, runner: Annotated[ValidationRunner, Depends(get_runner)]):
    ds = runner.config.data_sources.get(name)
    if ds is None:
        raise HTTPException(status_code=404, detail=f"unknown data source '{name}'")
    return _public(name, ds)


@router.put("/{name}")
def upsert_datasource(
    name: str,
    payload: DataSourceConfig,
    runner: Annotated[ValidationRunner, Depends(get_runner)],
):
    def mutate(data: dict[str, Any]) -> None:
        data["data_sources"][name] = payload.model_dump(mode="json")

    apply_config_change(runner, mutate)
    return _public(name, runner.config.data_sources[name])


@router.delete("/{name}")
def delete_datasource(name: str, runner: Annotated[ValidationRunner, Depends(get_runner)]):
    if name not in runner.config.data_sources:
        raise HTTPException(status_code=404, detail=f"unknown data source '{name}'")

    referenced_by = [
        item_name
        for item_name, item in runner.config.validations.items()
        if item.source.data_source == name or item.target.data_source == name
    ]
    if referenced_by:
        raise HTTPException(
            status_code=409,
            detail=f"data source '{name}' is referenced by validation item(s): {referenced_by}",
        )

    def mutate(data: dict[str, Any]) -> None:
        del data["data_sources"][name]

    apply_config_change(runner, mutate)
    return {"detail": f"data source '{name}' deleted"}


@router.post("/{name}/test", response_model=ConnectionTestResult)
def test_datasource(name: str, runner: Annotated[ValidationRunner, Depends(get_runner)]):
    if name not in runner.config.data_sources:
        raise HTTPException(status_code=404, detail=f"unknown data source '{name}'")
    try:
        runner.test_connection(name)
    except DataSourceError as exc:
        return ConnectionTestResult(data_source=name, ok=False, detail=str(exc))
    return ConnectionTestResult(data_source=name, ok=True)
