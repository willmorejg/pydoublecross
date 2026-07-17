# SPDX-FileCopyrightText: 2026 James G Willmore
# SPDX-License-Identifier: Apache-2.0

"""Request/response models specific to the REST API (not part of the config schema)."""

from __future__ import annotations

from pydantic import BaseModel


class DataSourceSummary(BaseModel):
    name: str
    type: str
    cache_enabled: bool
    uses_url: bool


class ValidationItemSummary(BaseModel):
    name: str
    description: str | None
    source_data_source: str
    target_data_source: str


class ConnectionTestResult(BaseModel):
    data_source: str
    ok: bool
    detail: str | None = None


class CacheClearResult(BaseModel):
    removed: int


class MessageResponse(BaseModel):
    detail: str
