# SPDX-FileCopyrightText: 2026 James G Willmore
# SPDX-License-Identifier: Apache-2.0

"""Cache orchestration: decides whether to read/write the cache for a given fetch."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from pathlib import Path

import pandas as pd

from pydoublecross.cache.file_cache import FileCacheBackend
from pydoublecross.config.models import ResolvedCacheOptions
from pydoublecross.logging_conf import get_logger

logger = get_logger(__name__)


def cache_key(data_source_name: str, query: str) -> str:
    digest = hashlib.sha256(query.encode("utf-8")).hexdigest()[:16]
    return f"{data_source_name}/{digest}"


class CacheManager:
    """Applies `ResolvedCacheOptions` around a dataframe-fetching callable."""

    def __init__(self, cache_dir: Path) -> None:
        self.backend = FileCacheBackend(cache_dir)

    def get_or_fetch(
        self,
        data_source_name: str,
        query: str,
        options: ResolvedCacheOptions,
        fetch_fn: Callable[[], pd.DataFrame],
    ) -> tuple[pd.DataFrame, bool]:
        """Return (dataframe, was_cache_hit)."""
        if not options.enabled:
            return fetch_fn(), False

        key = cache_key(data_source_name, query)

        if not options.force_refresh:
            cached = self.backend.get(key, options.ttl_seconds)
            if cached is not None:
                logger.debug("cache hit for %s", key)
                return cached, True

        frame = fetch_fn()
        self.backend.put(key, frame)
        return frame, False

    def clear(self, data_source_name: str | None = None) -> int:
        return self.backend.clear(data_source_name)
