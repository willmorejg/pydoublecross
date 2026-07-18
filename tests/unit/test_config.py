# SPDX-FileCopyrightText: 2026 James G Willmore
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from pydoublecross.config.loader import load_config, save_config
from pydoublecross.config.models import AppConfig, DataSourceConfig, DataSourceRef
from pydoublecross.exceptions import ConfigError


def test_load_config_valid(config_path: Path) -> None:
    config = load_config(config_path)
    assert "src" in config.data_sources
    assert "customer_check" in config.validations
    assert config.validations["customer_check"].key_columns == ["customer_id"]


def test_load_config_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        load_config(tmp_path / "does_not_exist.yaml")


def test_load_config_unknown_datasource_reference(tmp_path: Path) -> None:
    data = {
        "data_sources": {"src": {"type": "sqlite", "path": str(tmp_path / "a.db")}},
        "validations": {
            "bad": {
                "source": {"data_source": "src", "table": "t"},
                "target": {"data_source": "missing", "table": "t"},
                "key_columns": ["id"],
            }
        },
    }
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(path)


def test_env_var_interpolation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PDC_TEST_PASSWORD", "s3cret")
    data = {
        "data_sources": {
            "pg": {
                "type": "postgresql",
                "host": "localhost",
                "password": "${env:PDC_TEST_PASSWORD}",
            }
        }
    }
    path = tmp_path / "env.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    config = load_config(path)
    assert config.data_sources["pg"].password == "s3cret"


def test_env_var_interpolation_missing_raises(tmp_path: Path) -> None:
    os.environ.pop("PDC_TEST_UNSET", None)
    data = {
        "data_sources": {
            "pg": {"type": "postgresql", "host": "localhost", "password": "${env:PDC_TEST_UNSET}"}
        }
    }
    path = tmp_path / "env_missing.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(path)


def test_datasource_requires_path_for_file_based() -> None:
    with pytest.raises(ValueError, match="requires 'path'"):
        DataSourceConfig(type="sqlite")


def test_datasource_requires_host_for_server_based() -> None:
    with pytest.raises(ValueError, match="requires 'host'"):
        DataSourceConfig(type="postgresql")


def test_datasource_url_bypasses_host_and_path_requirements() -> None:
    # Neither 'path' (sqlite) nor 'host' (postgresql) is required when 'url' is set.
    sqlite_ds = DataSourceConfig(type="sqlite", url="sqlite:///:memory:")
    assert sqlite_ds.path is None

    pg_ds = DataSourceConfig(type="postgresql", url="postgresql+psycopg://u:p@h:5432/d")
    assert pg_ds.host is None


def test_datasource_invalid_url_raises() -> None:
    with pytest.raises(ValueError, match="invalid 'url'"):
        DataSourceConfig(type="postgresql", url="not a valid sqlalchemy url::::")


def test_datasource_url_supports_env_interpolation(tmp_path: Path) -> None:
    import os

    os.environ["PDC_TEST_URL_PASSWORD"] = (
        "s3cret"  # NOSONAR - dummy value, only used to prove ${env:...} interpolation works
    )
    try:
        data = {
            "data_sources": {
                "pg": {
                    "type": "postgresql",
                    "url": "postgresql+psycopg://u:${env:PDC_TEST_URL_PASSWORD}@h:5432/d",
                }
            }
        }
        path = tmp_path / "url_env.yaml"
        path.write_text(yaml.safe_dump(data), encoding="utf-8")
        config = load_config(path)
        url = config.data_sources["pg"].url
        assert url is not None
        assert "s3cret" in url
    finally:
        del os.environ["PDC_TEST_URL_PASSWORD"]


def test_datasource_ref_requires_exactly_one_of_sql_or_table() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        DataSourceRef(data_source="src", sql="SELECT 1", table="t")
    with pytest.raises(ValueError, match="exactly one"):
        DataSourceRef(data_source="src")


def test_cache_override_resolves_against_defaults(config_path: Path) -> None:
    config = load_config(config_path)
    item = config.validations["customer_check"]
    source_cache = config.resolve_cache(item.source)
    target_cache = config.resolve_cache(item.target)
    assert source_cache.enabled is True
    assert target_cache.enabled is False


def test_save_config_roundtrip(tmp_path: Path, config_path: Path) -> None:
    config = load_config(config_path)
    out_path = tmp_path / "roundtrip.yaml"
    save_config(config, out_path)
    reloaded = AppConfig.model_validate(yaml.safe_load(out_path.read_text(encoding="utf-8")))
    assert reloaded.data_sources.keys() == config.data_sources.keys()
    assert reloaded.validations.keys() == config.validations.keys()


def test_relative_sqlite_path_resolved_against_config_dir(tmp_path: Path) -> None:
    (tmp_path / "data.db").touch()
    data = {"data_sources": {"src": {"type": "sqlite", "path": "data.db"}}}
    path = tmp_path / "rel.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    config = load_config(path)
    resolved_path = config.data_sources["src"].path
    assert resolved_path is not None
    assert Path(resolved_path).is_absolute()
    assert Path(resolved_path) == (tmp_path / "data.db").resolve()
