# SPDX-FileCopyrightText: 2026 James G Willmore
# SPDX-License-Identifier: Apache-2.0

"""Single orchestration entry point used by the CLI, REST API, and web app."""

from __future__ import annotations

from pathlib import Path

from pydoublecross.cache.manager import CacheManager
from pydoublecross.config.loader import load_config, save_config
from pydoublecross.config.models import AppConfig
from pydoublecross.datasources.factory import DataSourceFactory
from pydoublecross.exceptions import ReportExportError
from pydoublecross.reporting.exporters import EXPORTERS
from pydoublecross.validation.engine import CacheMode, ValidationEngine
from pydoublecross.validation.results import ValidationRunResult


class ValidationRunner:
    """Wires config, data sources, caching, and the validation engine together."""

    def __init__(self, config: AppConfig, config_path: Path | None = None) -> None:
        self.config_path = config_path
        self.config = config
        self._datasources = DataSourceFactory(config)
        self._cache = CacheManager(config.app.cache_dir)
        self._engine = ValidationEngine(config, self._datasources, self._cache)
        self.config.app.results_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_config_path(cls, path: str | Path) -> ValidationRunner:
        config_path = Path(path).expanduser()
        return cls(load_config(config_path), config_path=config_path)

    def replace_config(self, new_config: AppConfig) -> None:
        """Swap in a new validated config (used after a CRUD edit) and rebuild dependents."""
        self.dispose()
        self.config = new_config
        self._datasources = DataSourceFactory(new_config)
        self._cache = CacheManager(new_config.app.cache_dir)
        self._engine = ValidationEngine(new_config, self._datasources, self._cache)
        self.config.app.results_dir.mkdir(parents=True, exist_ok=True)

    def save(self) -> None:
        if self.config_path is None:
            raise ReportExportError("no config_path set; cannot save configuration")
        save_config(self.config, self.config_path)

    def list_items(self) -> list[dict]:
        return [
            {
                "name": name,
                "description": item.description,
                "source_data_source": item.source.data_source,
                "target_data_source": item.target.data_source,
            }
            for name, item in self.config.validations.items()
        ]

    def run(self, item_name: str, cache_mode: CacheMode = "default") -> ValidationRunResult:
        result = self._engine.run(item_name, cache_mode)
        self._persist_result(result)
        return result

    def run_all(self, cache_mode: CacheMode = "default") -> list[ValidationRunResult]:
        return [self.run(name, cache_mode) for name in self.config.validations]

    def _persist_result(self, result: ValidationRunResult) -> Path:
        item_dir = self.config.app.results_dir / result.item_name
        item_dir.mkdir(parents=True, exist_ok=True)
        path = item_dir / f"{result.run_id}.json"
        path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        return path

    def history(self, item_name: str, limit: int = 20) -> list[ValidationRunResult]:
        item_dir = self.config.app.results_dir / item_name
        if not item_dir.is_dir():
            return []
        files = sorted(item_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        return [
            ValidationRunResult.model_validate_json(f.read_text(encoding="utf-8"))
            for f in files[:limit]
        ]

    def get_result(self, item_name: str, run_id: str) -> ValidationRunResult | None:
        path = self.config.app.results_dir / item_name / f"{run_id}.json"
        if not path.is_file():
            return None
        return ValidationRunResult.model_validate_json(path.read_text(encoding="utf-8"))

    def export(self, result: ValidationRunResult, fmt: str, destination: Path) -> Path:
        try:
            exporter_cls = EXPORTERS[fmt]
        except KeyError as exc:
            raise ReportExportError(
                f"unsupported export format '{fmt}' (available: {list(EXPORTERS)})"
            ) from exc
        return exporter_cls().export(result, destination)

    def test_connection(self, data_source_name: str) -> bool:
        return self._datasources.get(data_source_name).test_connection()

    def clear_cache(self, data_source_name: str | None = None) -> int:
        return self._cache.clear(data_source_name)

    def dispose(self) -> None:
        self._datasources.dispose_all()
