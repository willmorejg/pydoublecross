# SPDX-FileCopyrightText: 2026 James G Willmore
# SPDX-License-Identifier: Apache-2.0

"""Local filesystem cache backend: one Parquet file + a JSON metadata sidecar per key."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd

from pydoublecross.exceptions import CacheError


class FileCacheBackend:
    """Stores dataframes as Parquet under `root`, keyed by a relative path-like string.

    A key such as ``"my_data_source/ab12cd34"`` is stored as
    ``root/my_data_source/ab12cd34.parquet`` plus a ``.json`` metadata sidecar.
    """

    def __init__(self, root: Path) -> None:
        self.root = root

    def _paths(self, key: str) -> tuple[Path, Path]:
        base = self.root / key
        return base.with_suffix(".parquet"), base.with_suffix(".json")

    def get(self, key: str, ttl_seconds: int) -> pd.DataFrame | None:
        data_path, meta_path = self._paths(key)
        if not data_path.is_file() or not meta_path.is_file():
            return None

        try:
            metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

        age = time.time() - metadata.get("fetched_at", 0)
        if age > ttl_seconds:
            return None

        try:
            return pd.read_parquet(data_path)
        except Exception as exc:
            raise CacheError(f"failed to read cache entry '{key}': {exc}") from exc

    def put(self, key: str, frame: pd.DataFrame) -> None:
        data_path, meta_path = self._paths(key)
        data_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            frame.to_parquet(data_path, index=False)
            meta_path.write_text(
                json.dumps({"fetched_at": time.time(), "row_count": len(frame)}),
                encoding="utf-8",
            )
        except Exception as exc:
            raise CacheError(f"failed to write cache entry '{key}': {exc}") from exc

    def clear(self, prefix: str | None = None) -> int:
        """Remove all entries under `prefix` (a data source name or a full key).

        `prefix=None` clears everything. A `prefix` that names a directory (e.g. a
        data source name, since entries are stored as ``<data_source>/<hash>``)
        clears every entry under it; otherwise it's treated as one exact key.
        """
        target_dir = self.root if prefix is None else self.root / prefix
        if target_dir.is_dir():
            removed = 0
            for path in target_dir.rglob("*"):
                if path.is_file():
                    path.unlink()
                    removed += 1
            return removed

        if prefix is None:
            return 0

        data_path, meta_path = self._paths(prefix)
        removed = 0
        for path in (data_path, meta_path):
            if path.is_file():
                path.unlink()
                removed += 1
        return removed
