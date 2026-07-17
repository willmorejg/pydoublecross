# SPDX-FileCopyrightText: 2026 James G Willmore
# SPDX-License-Identifier: Apache-2.0

"""Shared FastAPI dependencies."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import HTTPException, Request
from pydantic import ValidationError

from pydoublecross.config.models import AppConfig
from pydoublecross.core.runner import ValidationRunner


def get_runner(request: Request) -> ValidationRunner:
    return request.app.state.runner


def apply_config_change(runner: ValidationRunner, mutate: Callable[[dict[str, Any]], None]) -> None:
    """Apply `mutate` to a dict copy of the current config, re-validate, swap in, and persist."""
    data = runner.config.model_dump(mode="json")
    mutate(data)
    try:
        new_config = AppConfig.model_validate(data)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    runner.replace_config(new_config)
    runner.save()
