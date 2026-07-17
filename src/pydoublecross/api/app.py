# SPDX-FileCopyrightText: 2026 James G Willmore
# SPDX-License-Identifier: Apache-2.0

"""FastAPI application factory for the REST API."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from pydoublecross import __version__
from pydoublecross.api.routers import cache, datasources, reports, validations
from pydoublecross.core.runner import ValidationRunner

_UNPROTECTED_PATHS = {"/api/health"}


async def _api_key_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    runner: ValidationRunner = request.app.state.runner
    expected_key = runner.config.server.api_key
    path = request.url.path
    protected = expected_key and path.startswith("/api") and path not in _UNPROTECTED_PATHS
    if protected and request.headers.get("X-API-Key") != expected_key:
        return JSONResponse({"detail": "invalid or missing API key"}, status_code=401)
    return await call_next(request)


def create_api_app(runner: ValidationRunner) -> FastAPI:
    """Build a FastAPI app exposing the REST API for one `ValidationRunner`."""
    app = FastAPI(title="pyDoubleCross", version=__version__)
    app.state.runner = runner

    if runner.config.server.api_key:
        app.middleware("http")(_api_key_middleware)

    app.include_router(datasources.router)
    app.include_router(validations.router)
    app.include_router(cache.router)
    app.include_router(reports.router)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    return app
