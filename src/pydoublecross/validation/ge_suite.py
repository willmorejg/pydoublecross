# SPDX-FileCopyrightText: 2026 James G Willmore
# SPDX-License-Identifier: Apache-2.0

"""Per-side Great Expectations checks (schema, nullness, row count).

Great Expectations validates one batch against a suite; it does not diff two
batches against each other, so this module only covers checks that make
sense against a single dataframe. Cross-source comparison lives in
`comparators.py`.
"""

from __future__ import annotations

import uuid
from typing import Literal

import great_expectations as gx
import great_expectations.expectations as gxe
import pandas as pd
from great_expectations.data_context.types.base import ProgressBarsConfig

from pydoublecross.config.models import ExpectationToggles
from pydoublecross.exceptions import ValidationEngineError
from pydoublecross.validation.results import GESideResult


def run_side_expectations(
    frame: pd.DataFrame,
    role: Literal["source", "target"],
    toggles: ExpectationToggles,
) -> GESideResult:
    """Run the configured built-in expectation checks against one side's dataframe."""
    suffix = uuid.uuid4().hex[:8]
    try:
        context = gx.get_context(mode="ephemeral")
        context.variables.progress_bars = ProgressBarsConfig(
            globally=False, metric_calculations=False
        )
        data_source = context.data_sources.add_pandas(f"pdc-{role}-{suffix}")
        asset = data_source.add_dataframe_asset(name=f"asset-{suffix}")
        batch_definition = asset.add_batch_definition_whole_dataframe(f"batch-{suffix}")
        suite = context.suites.add(gx.ExpectationSuite(name=f"suite-{suffix}"))

        # GX's Expectation classes build their pydantic fields dynamically via a
        # metaclass, which static analysis cannot see - these calls are runtime-verified.
        if toggles.row_count_match:
            suite.add_expectation(gxe.ExpectTableRowCountToBeBetween(min_value=1))  # ty: ignore[unknown-argument]
        if toggles.schema_match:
            suite.add_expectation(
                gxe.ExpectTableColumnsToMatchSet(
                    column_set=list(frame.columns),  # ty: ignore[unknown-argument]
                    exact_match=False,  # ty: ignore[unknown-argument]
                )
            )
        if toggles.null_checks:
            for column in frame.columns:
                if frame[column].isna().all():
                    continue
                suite.add_expectation(
                    gxe.ExpectColumnValuesToNotBeNull(column=column)  # ty: ignore[unknown-argument]
                )

        validation_definition = context.validation_definitions.add(
            gx.ValidationDefinition(
                name=f"validation-{suffix}",
                data=batch_definition,
                suite=suite,
            )
        )
        run_result = validation_definition.run(batch_parameters={"dataframe": frame})

        results = list(run_result.results)
        failed_types = [
            r.expectation_config.type for r in results if not r.success and r.expectation_config
        ]
        return GESideResult(
            role=role,
            success=bool(run_result.success),
            expectations_evaluated=len(results),
            expectations_failed=len(failed_types),
            failed_expectation_types=failed_types,
        )
    except ValidationEngineError:
        raise
    except Exception as exc:
        raise ValidationEngineError(
            f"Great Expectations validation failed for {role} side: {exc}"
        ) from exc
