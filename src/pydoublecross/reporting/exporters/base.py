# SPDX-FileCopyrightText: 2026 James G Willmore
# SPDX-License-Identifier: Apache-2.0

"""Exporter interface, so new output formats don't touch the validation engine."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from pydoublecross.validation.results import ValidationRunResult


class Exporter(ABC):
    format_name: str

    @abstractmethod
    def export(self, result: ValidationRunResult, destination: Path) -> Path:
        """Write `result` to `destination` and return the path actually written."""
