# SPDX-FileCopyrightText: 2026 James G Willmore
# SPDX-License-Identifier: Apache-2.0

"""Combined FastAPI app: REST API + server-rendered web UI."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from pydoublecross.api.app import create_api_app
from pydoublecross.core.runner import ValidationRunner
from pydoublecross.logging_conf import configure_logging
from pydoublecross.settings import RuntimeSettings
from pydoublecross.web.routes import router as web_router

STATIC_DIR = Path(__file__).parent / "static"


def create_app(runner: ValidationRunner) -> FastAPI:
    app = create_api_app(runner)
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    app.include_router(web_router)
    return app


def build_app_from_env() -> FastAPI:
    """Factory used by `uvicorn --factory`; reads config path from the environment."""
    settings = RuntimeSettings()
    configure_logging(settings.log_level)
    runner = ValidationRunner.from_config_path(settings.config_path)
    return create_app(runner)
