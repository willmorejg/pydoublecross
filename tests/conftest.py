# SPDX-FileCopyrightText: 2026 James G Willmore
# SPDX-License-Identifier: Apache-2.0

"""Shared pytest fixtures: a source/target SQLite pair and a matching config."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest
import yaml

from pydoublecross.core.runner import ValidationRunner

SOURCE_ROWS = [
    (1, "Alice", "alice@example.com"),
    (2, "Bob", "bob@example.com"),
    (3, "Carol", "carol@example.com"),
]
TARGET_ROWS = [
    (1, "Alice", "alice@example.com"),
    (2, "Bob", "bob@WRONG.com"),
    (4, "Dave", "dave@example.com"),
]


def _make_sqlite_db(path: Path, rows: list[tuple[int, str, str]]) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.execute("CREATE TABLE customers (customer_id INTEGER, name TEXT, email TEXT)")
        conn.executemany("INSERT INTO customers VALUES (?, ?, ?)", rows)
        conn.commit()
    finally:
        conn.close()


@pytest.fixture
def sqlite_pair(tmp_path: Path) -> tuple[Path, Path]:
    source_db = tmp_path / "source.db"
    target_db = tmp_path / "target.db"
    _make_sqlite_db(source_db, SOURCE_ROWS)
    _make_sqlite_db(target_db, TARGET_ROWS)
    return source_db, target_db


@pytest.fixture
def config_path(tmp_path: Path, sqlite_pair: tuple[Path, Path]) -> Path:
    source_db, target_db = sqlite_pair
    config = {
        "app": {
            "cache_dir": str(tmp_path / "cache"),
            "results_dir": str(tmp_path / "results"),
        },
        "data_sources": {
            "src": {"type": "sqlite", "path": str(source_db), "cache": {"enabled": True}},
            "tgt": {"type": "sqlite", "path": str(target_db), "cache": {"enabled": False}},
        },
        "validations": {
            "customer_check": {
                "description": "test",
                "source": {"data_source": "src", "table": "customers"},
                "target": {"data_source": "tgt", "table": "customers"},
                "key_columns": ["customer_id"],
            },
            "customer_check_pandera": {
                "description": "test, pandera engine",
                "source": {"data_source": "src", "table": "customers"},
                "target": {"data_source": "tgt", "table": "customers"},
                "key_columns": ["customer_id"],
                "validation_engine": "pandera",
            },
            "customer_check_both": {
                "description": "test, both engines",
                "source": {"data_source": "src", "table": "customers"},
                "target": {"data_source": "tgt", "table": "customers"},
                "key_columns": ["customer_id"],
                "validation_engine": "both",
            },
        },
    }
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return path


@pytest.fixture
def runner(config_path: Path) -> Iterator[ValidationRunner]:
    r = ValidationRunner.from_config_path(config_path)
    yield r
    r.dispose()
