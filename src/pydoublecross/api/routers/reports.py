# SPDX-FileCopyrightText: 2026 James G Willmore
# SPDX-License-Identifier: Apache-2.0

"""Export a stored validation run result to a downloadable report file."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from pydoublecross.api.deps import get_runner
from pydoublecross.core.runner import ValidationRunner
from pydoublecross.exceptions import ReportExportError

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get(
    "/{name}/{run_id}",
    responses={
        400: {"description": "Unsupported export format"},
        404: {"description": "No such run result"},
    },
)
def export_report(
    name: str,
    run_id: str,
    runner: Annotated[ValidationRunner, Depends(get_runner)],
    format: str = "excel",
):
    result = runner.get_result(name, run_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"no result '{run_id}' for '{name}'")

    destination = runner.config.app.results_dir / name / f"{run_id}_export"
    try:
        path = runner.export(result, format, destination)
    except ReportExportError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return FileResponse(path, filename=path.name)
