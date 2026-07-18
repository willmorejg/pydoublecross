# SPDX-FileCopyrightText: 2026 James G Willmore
# SPDX-License-Identifier: Apache-2.0

"""CRUD, run, and result history for validation items."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException

from pydoublecross.api.deps import apply_config_change, get_runner
from pydoublecross.api.schemas import ValidationItemSummary
from pydoublecross.config.models import ValidationItemConfig
from pydoublecross.core.runner import ValidationRunner
from pydoublecross.exceptions import PyDoubleCrossError
from pydoublecross.validation.engine import resolve_cache_mode
from pydoublecross.validation.results import ValidationRunResult

router = APIRouter(prefix="/api/validations", tags=["validations"])


@router.get("", response_model=list[ValidationItemSummary])
def list_validations(runner: Annotated[ValidationRunner, Depends(get_runner)]):
    return [ValidationItemSummary(**item) for item in runner.list_items()]


@router.get(
    "/{name}",
    response_model=ValidationItemConfig,
    responses={404: {"description": "Unknown validation item"}},
)
def get_validation(name: str, runner: Annotated[ValidationRunner, Depends(get_runner)]):
    item = runner.config.validations.get(name)
    if item is None:
        raise HTTPException(status_code=404, detail=f"unknown validation item '{name}'")
    return item


@router.put(
    "/{name}",
    response_model=ValidationItemConfig,
    responses={422: {"description": "Resulting configuration is invalid"}},
)
def upsert_validation(
    name: str,
    payload: ValidationItemConfig,
    runner: Annotated[ValidationRunner, Depends(get_runner)],
):
    def mutate(data: dict[str, Any]) -> None:
        data["validations"][name] = payload.model_dump(mode="json")

    apply_config_change(runner, mutate)
    return runner.config.validations[name]


@router.delete(
    "/{name}",
    responses={
        404: {"description": "Unknown validation item"},
        422: {"description": "Resulting configuration is invalid"},
    },
)
def delete_validation(name: str, runner: Annotated[ValidationRunner, Depends(get_runner)]):
    if name not in runner.config.validations:
        raise HTTPException(status_code=404, detail=f"unknown validation item '{name}'")

    def mutate(data: dict[str, Any]) -> None:
        del data["validations"][name]

    apply_config_change(runner, mutate)
    return {"detail": f"validation item '{name}' deleted"}


@router.post(
    "/{name}/run",
    response_model=ValidationRunResult,
    responses={
        400: {"description": "The run failed"},
        404: {"description": "Unknown validation item"},
    },
)
def run_validation(
    name: str,
    runner: Annotated[ValidationRunner, Depends(get_runner)],
    no_cache: bool = False,
    refresh_cache: bool = False,
):
    if name not in runner.config.validations:
        raise HTTPException(status_code=404, detail=f"unknown validation item '{name}'")
    cache_mode = resolve_cache_mode(no_cache, refresh_cache)
    try:
        return runner.run(name, cache_mode=cache_mode)
    except PyDoubleCrossError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{name}/results", response_model=list[ValidationRunResult])
def list_results(
    name: str,
    runner: Annotated[ValidationRunner, Depends(get_runner)],
    limit: int = 20,
):
    return runner.history(name, limit=limit)


@router.get(
    "/{name}/results/{run_id}",
    response_model=ValidationRunResult,
    responses={404: {"description": "No such run result"}},
)
def get_result(name: str, run_id: str, runner: Annotated[ValidationRunner, Depends(get_runner)]):
    result = runner.get_result(name, run_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"no result '{run_id}' for '{name}'")
    return result
