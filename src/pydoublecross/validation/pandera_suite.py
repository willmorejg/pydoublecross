# SPDX-FileCopyrightText: 2026 James G Willmore
# SPDX-License-Identifier: Apache-2.0

"""Per-side Pandera checks (schema, nullness, row count).

Like Great Expectations (`ge_suite.py`), Pandera validates one dataframe against a
schema - it doesn't diff two dataframes against each other. Cross-source comparison
lives in `comparators.py`. This module exists so `validation_engine: pandera` (or
`both`) runs the exact same three toggles (`row_count_match`/`schema_match`/
`null_checks`) as the Great Expectations path, just checked by a different library.
"""

from __future__ import annotations

from typing import Literal

import pandas as pd
import pandera.pandas as pa
from pandera.errors import SchemaErrors

from pydoublecross.config.models import ExpectationToggles
from pydoublecross.exceptions import ValidationEngineError
from pydoublecross.validation.results import EngineCheckResult


def run_side_checks(
    frame: pd.DataFrame,
    role: Literal["source", "target"],
    toggles: ExpectationToggles,
) -> EngineCheckResult:
    """Run the configured built-in checks against one side's dataframe."""
    try:
        columns: dict[str, pa.Column] = {}
        checks_evaluated = 0

        for column in frame.columns:
            nullable = True
            if toggles.null_checks and not frame[column].isna().all():
                nullable = False
                checks_evaluated += 1
            columns[column] = pa.Column(nullable=nullable)

        dataframe_checks = []
        if toggles.row_count_match:
            dataframe_checks.append(pa.Check(lambda d: len(d) > 0, name="row_count_positive"))
            checks_evaluated += 1
        # Same limitation as the Great Expectations side: with no externally-declared
        # expected schema to diff against, `strict` only catches a fetch that grew an
        # extra column relative to *this same* frame - i.e. never, today. Kept for
        # parity/documentation; see docs/validation.md.
        strict = toggles.schema_match
        if toggles.schema_match:
            checks_evaluated += 1

        schema = pa.DataFrameSchema(columns=columns, checks=dataframe_checks, strict=strict)

        try:
            schema.validate(frame, lazy=True)
        except SchemaErrors as exc:
            failure_cases = exc.failure_cases
            failed_names = sorted({str(v) for v in failure_cases["check"].dropna()})
            return EngineCheckResult(
                engine="pandera",
                role=role,
                success=False,
                checks_evaluated=checks_evaluated,
                checks_failed=len(failure_cases),
                failed_check_names=failed_names,
            )

        return EngineCheckResult(
            engine="pandera",
            role=role,
            success=True,
            checks_evaluated=checks_evaluated,
            checks_failed=0,
        )
    except ValidationEngineError:
        raise
    except Exception as exc:
        raise ValidationEngineError(f"Pandera validation failed for {role} side: {exc}") from exc
