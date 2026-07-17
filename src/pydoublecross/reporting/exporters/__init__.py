# SPDX-FileCopyrightText: 2026 James G Willmore
# SPDX-License-Identifier: Apache-2.0

from pydoublecross.reporting.exporters.base import Exporter
from pydoublecross.reporting.exporters.excel import ExcelExporter

EXPORTERS: dict[str, type[Exporter]] = {
    ExcelExporter.format_name: ExcelExporter,
}

__all__ = ["EXPORTERS", "ExcelExporter", "Exporter"]
