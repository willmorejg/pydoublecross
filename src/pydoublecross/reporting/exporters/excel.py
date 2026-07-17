# SPDX-FileCopyrightText: 2026 James G Willmore
# SPDX-License-Identifier: Apache-2.0

"""Export a `ValidationRunResult` to a multi-sheet Excel workbook."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from pydoublecross.exceptions import ReportExportError
from pydoublecross.reporting.exporters.base import Exporter
from pydoublecross.reporting.report import ge_result_rows, mismatch_rows, summary_rows
from pydoublecross.validation.results import ValidationRunResult

_EMPTY_NOTE = pd.DataFrame([{"note": "no rows"}])


def _sheet(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows) if rows else _EMPTY_NOTE


class ExcelExporter(Exporter):
    format_name = "excel"

    def export(self, result: ValidationRunResult, destination: Path) -> Path:
        destination = destination.with_suffix(".xlsx")
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            with pd.ExcelWriter(destination, engine="openpyxl") as writer:
                _sheet(summary_rows(result)).to_excel(writer, sheet_name="Summary", index=False)
                _sheet(result.missing_in_target).to_excel(
                    writer, sheet_name="Missing In Target", index=False
                )
                _sheet(result.missing_in_source).to_excel(
                    writer, sheet_name="Missing In Source", index=False
                )
                _sheet(mismatch_rows(result)).to_excel(
                    writer, sheet_name="Value Mismatches", index=False
                )
                _sheet(ge_result_rows(result)).to_excel(
                    writer, sheet_name="GE Expectations", index=False
                )
        except Exception as exc:
            raise ReportExportError(f"failed to export Excel report: {exc}") from exc
        return destination
