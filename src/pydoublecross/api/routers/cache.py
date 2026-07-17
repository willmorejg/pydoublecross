# SPDX-FileCopyrightText: 2026 James G Willmore
# SPDX-License-Identifier: Apache-2.0

"""Cache inspection and clearing."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from pydoublecross.api.deps import get_runner
from pydoublecross.api.schemas import CacheClearResult
from pydoublecross.core.runner import ValidationRunner

router = APIRouter(prefix="/api/cache", tags=["cache"])


@router.delete("", response_model=CacheClearResult)
def clear_cache(
    runner: Annotated[ValidationRunner, Depends(get_runner)],
    data_source: str | None = None,
):
    removed = runner.clear_cache(data_source)
    return CacheClearResult(removed=removed)
