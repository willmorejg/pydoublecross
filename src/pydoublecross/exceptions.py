# SPDX-FileCopyrightText: 2026 James G Willmore
# SPDX-License-Identifier: Apache-2.0

"""Application-wide exception types."""

from __future__ import annotations


class PyDoubleCrossError(Exception):
    """Base class for all pyDoubleCross errors."""


class ConfigError(PyDoubleCrossError):
    """Raised when the YAML configuration is missing, invalid, or unresolvable."""


class DataSourceError(PyDoubleCrossError):
    """Raised when a data source connection or query fails."""


class CacheError(PyDoubleCrossError):
    """Raised when reading from or writing to the cache fails."""


class ValidationEngineError(PyDoubleCrossError):
    """Raised when a validation run cannot be completed."""


class ReportExportError(PyDoubleCrossError):
    """Raised when a report cannot be exported in the requested format."""
