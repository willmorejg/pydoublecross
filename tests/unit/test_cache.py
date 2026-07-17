# SPDX-FileCopyrightText: 2026 James G Willmore
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd

from pydoublecross.cache.file_cache import FileCacheBackend
from pydoublecross.cache.manager import CacheManager
from pydoublecross.config.models import ResolvedCacheOptions


def test_file_cache_put_and_get_roundtrip(tmp_path: Path) -> None:
    backend = FileCacheBackend(tmp_path)
    frame = pd.DataFrame({"a": [1, 2, 3]})
    backend.put("ds/key1", frame)
    cached = backend.get("ds/key1", ttl_seconds=3600)
    assert cached is not None
    pd.testing.assert_frame_equal(cached, frame)


def test_file_cache_miss_returns_none(tmp_path: Path) -> None:
    backend = FileCacheBackend(tmp_path)
    assert backend.get("ds/missing", ttl_seconds=3600) is None


def test_file_cache_expired_returns_none(tmp_path: Path) -> None:
    backend = FileCacheBackend(tmp_path)
    frame = pd.DataFrame({"a": [1]})
    backend.put("ds/key1", frame)
    assert backend.get("ds/key1", ttl_seconds=0) is None


def test_file_cache_clear_single_key(tmp_path: Path) -> None:
    backend = FileCacheBackend(tmp_path)
    backend.put("ds/key1", pd.DataFrame({"a": [1]}))
    backend.put("ds/key2", pd.DataFrame({"a": [2]}))
    removed = backend.clear("ds/key1")
    assert removed == 2  # parquet + json sidecar
    assert backend.get("ds/key1", ttl_seconds=3600) is None
    assert backend.get("ds/key2", ttl_seconds=3600) is not None


def test_file_cache_clear_all(tmp_path: Path) -> None:
    backend = FileCacheBackend(tmp_path)
    backend.put("dsA/key1", pd.DataFrame({"a": [1]}))
    backend.put("dsB/key1", pd.DataFrame({"a": [2]}))
    removed = backend.clear()
    assert removed == 4
    assert backend.get("dsA/key1", ttl_seconds=3600) is None


def test_cache_manager_disabled_always_fetches(tmp_path: Path) -> None:
    manager = CacheManager(tmp_path)
    calls = []

    def fetch() -> pd.DataFrame:
        calls.append(1)
        return pd.DataFrame({"a": [1]})

    options = ResolvedCacheOptions(enabled=False, ttl_seconds=3600)
    manager.get_or_fetch("src", "SELECT 1", options, fetch)
    manager.get_or_fetch("src", "SELECT 1", options, fetch)
    assert len(calls) == 2


def test_cache_manager_enabled_hits_on_second_call(tmp_path: Path) -> None:
    manager = CacheManager(tmp_path)
    calls = []

    def fetch() -> pd.DataFrame:
        calls.append(1)
        return pd.DataFrame({"a": [1]})

    options = ResolvedCacheOptions(enabled=True, ttl_seconds=3600)
    _, hit1 = manager.get_or_fetch("src", "SELECT 1", options, fetch)
    _, hit2 = manager.get_or_fetch("src", "SELECT 1", options, fetch)
    assert hit1 is False
    assert hit2 is True
    assert len(calls) == 1


def test_cache_manager_force_refresh_bypasses_read(tmp_path: Path) -> None:
    manager = CacheManager(tmp_path)
    calls = []

    def fetch() -> pd.DataFrame:
        calls.append(1)
        return pd.DataFrame({"a": [len(calls)]})

    options = ResolvedCacheOptions(enabled=True, ttl_seconds=3600, force_refresh=False)
    manager.get_or_fetch("src", "SELECT 1", options, fetch)

    refresh_options = ResolvedCacheOptions(enabled=True, ttl_seconds=3600, force_refresh=True)
    _, hit = manager.get_or_fetch("src", "SELECT 1", refresh_options, fetch)
    assert hit is False
    assert len(calls) == 2


def test_cache_key_differs_by_query(tmp_path: Path) -> None:
    from pydoublecross.cache.manager import cache_key

    assert cache_key("src", "SELECT 1") != cache_key("src", "SELECT 2")
    assert cache_key("src", "SELECT 1") != cache_key("other", "SELECT 1")


def test_cache_manager_clear(tmp_path: Path) -> None:
    manager = CacheManager(tmp_path)
    options = ResolvedCacheOptions(enabled=True, ttl_seconds=3600)
    manager.get_or_fetch("src", "SELECT 1", options, lambda: pd.DataFrame({"a": [1]}))
    removed = manager.clear("src")
    assert removed == 2


def test_ttl_boundary_not_expired(tmp_path: Path) -> None:
    backend = FileCacheBackend(tmp_path)
    backend.put("ds/key1", pd.DataFrame({"a": [1]}))
    time.sleep(0.05)
    assert backend.get("ds/key1", ttl_seconds=10) is not None
