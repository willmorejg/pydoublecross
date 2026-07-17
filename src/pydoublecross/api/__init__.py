# SPDX-FileCopyrightText: 2026 James G Willmore
# SPDX-License-Identifier: Apache-2.0

"""REST API for pyDoubleCross, built with FastAPI."""

from pydoublecross.api.app import create_api_app

__all__ = ["create_api_app"]
