# SPDX-FileCopyrightText: 2026 James G Willmore
# SPDX-License-Identifier: Apache-2.0

"""Ties together data fetch (with caching), Great Expectations checks, and comparison."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from pydoublecross.cache.manager import CacheManager
from pydoublecross.config.models import AppConfig, DataSourceRef, ValidationItemConfig
from pydoublecross.datasources.factory import DataSourceFactory
from pydoublecross.exceptions import ValidationEngineError
from pydoublecross.logging_conf import get_logger, sanitize_for_log
from pydoublecross.validation.comparators import compare_dataframes
from pydoublecross.validation.ge_suite import run_side_expectations
from pydoublecross.validation.results import RunStatus, ValidationRunResult

logger = get_logger(__name__)

CacheMode = Literal["default", "bypass", "refresh"]


def resolve_cache_mode(no_cache: bool, refresh_cache: bool) -> CacheMode:
    """Map the CLI's/API's `--no-cache`/`--refresh-cache` flags to a `CacheMode`."""
    if refresh_cache:
        return "refresh"
    if no_cache:
        return "bypass"
    return "default"


class ValidationEngine:
    """Runs one named validation item end to end."""

    def __init__(
        self,
        config: AppConfig,
        datasource_factory: DataSourceFactory,
        cache_manager: CacheManager,
    ) -> None:
        self._config = config
        self._datasources = datasource_factory
        self._cache = cache_manager

    def _fetch_side(self, ref: DataSourceRef, cache_mode: CacheMode) -> tuple:
        cache_options = self._config.resolve_cache(ref)
        if cache_mode == "bypass":
            cache_options = cache_options.model_copy(update={"enabled": False})
        elif cache_mode == "refresh":
            cache_options = cache_options.model_copy(
                update={"enabled": True, "force_refresh": True}
            )

        data_source = self._datasources.get(ref.data_source)
        frame, cache_hit = self._cache.get_or_fetch(
            ref.data_source,
            ref.query,
            cache_options,
            lambda: data_source.fetch_dataframe(ref.query),
        )
        return frame, cache_hit

    def run(self, item_name: str, cache_mode: CacheMode = "default") -> ValidationRunResult:
        try:
            item = self._config.validations[item_name]
        except KeyError as exc:
            raise ValidationEngineError(f"unknown validation item '{item_name}'") from exc

        run_id = uuid.uuid4().hex
        started_at = datetime.now(UTC)
        safe_item_name = sanitize_for_log(item_name)
        logger.info("running validation '%s' (run_id=%s)", safe_item_name, run_id)

        try:
            return self._run_item(item_name, item, run_id, started_at, cache_mode)
        except ValidationEngineError as exc:
            logger.exception("validation '%s' failed", safe_item_name)
            return ValidationRunResult(
                item_name=item_name,
                run_id=run_id,
                started_at=started_at,
                finished_at=datetime.now(UTC),
                status=RunStatus.ERROR,
                error=str(exc),
            )

    def _run_item(
        self,
        item_name: str,
        item: ValidationItemConfig,
        run_id: str,
        started_at: datetime,
        cache_mode: CacheMode,
    ) -> ValidationRunResult:
        source_frame, source_cache_hit = self._fetch_side(item.source, cache_mode)
        target_frame, target_cache_hit = self._fetch_side(item.target, cache_mode)

        ge_results = [
            run_side_expectations(source_frame, "source", item.expectations),
            run_side_expectations(target_frame, "target", item.expectations),
        ]

        outcome = compare_dataframes(
            source_frame,
            target_frame,
            key_columns=item.key_columns,
            compare_columns=item.compare_columns,
            ignore_columns=item.ignore_columns,
            numeric_tolerance=item.numeric_tolerance,
        )

        ge_passed = all(r.success for r in ge_results)
        status = (
            RunStatus.PASSED if outcome.summary.rows_fully_match and ge_passed else RunStatus.FAILED
        )

        return ValidationRunResult(
            item_name=item_name,
            run_id=run_id,
            started_at=started_at,
            finished_at=datetime.now(UTC),
            status=status,
            source_cache_hit=source_cache_hit,
            target_cache_hit=target_cache_hit,
            summary=outcome.summary,
            missing_in_target=outcome.missing_in_target,
            missing_in_source=outcome.missing_in_source,
            mismatches=outcome.mismatches,
            truncated=outcome.truncated,
            ge_results=ge_results,
        )
