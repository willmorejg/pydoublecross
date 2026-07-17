# SPDX-FileCopyrightText: 2026 James G Willmore
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import sqlite3
from pathlib import Path

from pydoublecross.config.models import DataSourceConfig
from pydoublecross.datasources.base import DataSource


def _make_sqlite_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.execute("CREATE TABLE widgets (id INTEGER, name TEXT)")
        conn.execute("INSERT INTO widgets VALUES (1, 'sprocket')")
        conn.commit()
    finally:
        conn.close()


def test_fetch_dataframe_with_individual_fields(tmp_path: Path) -> None:
    db_path = tmp_path / "widgets.db"
    _make_sqlite_db(db_path)

    config = DataSourceConfig(type="sqlite", path=str(db_path))
    ds = DataSource("widgets_db", config)
    frame = ds.fetch_dataframe("SELECT * FROM widgets")
    assert list(frame["name"]) == ["sprocket"]
    ds.dispose()


def test_fetch_dataframe_with_raw_url(tmp_path: Path) -> None:
    db_path = tmp_path / "widgets.db"
    _make_sqlite_db(db_path)

    # A raw url should work exactly like the equivalent individual-field config.
    config = DataSourceConfig(type="sqlite", url=f"sqlite:///{db_path}")
    ds = DataSource("widgets_db_via_url", config)
    frame = ds.fetch_dataframe("SELECT * FROM widgets")
    assert list(frame["name"]) == ["sprocket"]
    assert ds.test_connection() is True
    ds.dispose()


def test_raw_url_ignores_individual_fields(tmp_path: Path) -> None:
    db_path = tmp_path / "widgets.db"
    _make_sqlite_db(db_path)
    wrong_path = tmp_path / "does_not_exist.db"

    # path is deliberately wrong; url must win.
    config = DataSourceConfig(type="sqlite", url=f"sqlite:///{db_path}", path=str(wrong_path))
    ds = DataSource("widgets_db", config)
    frame = ds.fetch_dataframe("SELECT * FROM widgets")
    assert list(frame["name"]) == ["sprocket"]
    ds.dispose()
