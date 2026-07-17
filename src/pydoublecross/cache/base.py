# SPDX-FileCopyrightText: 2026 James G Willmore
# SPDX-License-Identifier: Apache-2.0

"""Cache backend interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class CacheBackend(ABC):
    """Storage backend for cached query results, keyed by an opaque string."""

    @abstractmethod
    def get(self, key: str, ttl_seconds: int) -> pd.DataFrame | None:
        """Return the cached dataframe for `key`, or None if absent/expired."""

    @abstractmethod
    def put(self, key: str, frame: pd.DataFrame) -> None:
        """Store `frame` under `key`, replacing any existing entry."""

    @abstractmethod
    def clear(self, prefix: str | None = None) -> int:
        """Remove entries under `prefix` (an exact key or a data-source name), or all. Returns count removed."""
