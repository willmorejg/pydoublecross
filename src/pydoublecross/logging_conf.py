# SPDX-FileCopyrightText: 2026 James G Willmore
# SPDX-License-Identifier: Apache-2.0

"""Central logging configuration."""

from __future__ import annotations

import logging

from rich.logging import RichHandler

_CONFIGURED = False


def configure_logging(level: str = "INFO") -> None:
    """Configure root logging once with a Rich console handler."""
    global _CONFIGURED
    if _CONFIGURED:
        logging.getLogger("pydoublecross").setLevel(level.upper())
        return

    logging.basicConfig(
        level=level.upper(),
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
    )
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("great_expectations").setLevel(logging.WARNING)
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def sanitize_for_log(value: str) -> str:
    """Strip CR/LF from user-controlled values before logging, to prevent log injection."""
    return value.replace("\r", "").replace("\n", "")
