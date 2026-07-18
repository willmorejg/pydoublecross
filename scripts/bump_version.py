# SPDX-FileCopyrightText: 2026 James G Willmore
# SPDX-License-Identifier: Apache-2.0

"""Compute and write the project's next CalVer+hash version.

Version scheme: ``YYYY.MM.MICRO+<7-char-git-sha>`` (a PEP 440 local version
identifier, e.g. ``2026.7.2+a1b2c3d``). ``MICRO`` resets to 1 when the
year/month changes and otherwise increments from whatever the current
``__version__`` in ``src/pydoublecross/__init__.py`` says - that file is the
single source of truth (``pyproject.toml`` reads it dynamically via
``[tool.hatch.version]``).

Usage: ``uv run python scripts/bump_version.py`` - rewrites `__init__.py` in
place and prints the new version to stdout.
"""

from __future__ import annotations

import argparse
import datetime
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INIT_PATH = REPO_ROOT / "src" / "pydoublecross" / "__init__.py"

VERSION_LINE_RE = re.compile(r'^__version__ = "([^"]+)"', re.MULTILINE)
CALVER_PREFIX_RE = re.compile(r"^(\d{4})\.(\d{1,2})\.(\d+)")


def read_current_version() -> str:
    text = INIT_PATH.read_text(encoding="utf-8")
    match = VERSION_LINE_RE.search(text)
    if not match:
        raise SystemExit(f'could not find a `__version__ = "..."` line in {INIT_PATH}')
    return match.group(1)


def next_calver(current_version: str, today: datetime.date) -> str:
    match = CALVER_PREFIX_RE.match(current_version)
    same_month = bool(match) and (int(match.group(1)), int(match.group(2))) == (
        today.year,
        today.month,
    )
    micro = int(match.group(3)) + 1 if same_month else 1
    return f"{today.year}.{today.month}.{micro}"


def git_short_sha(length: int = 7) -> str:
    return subprocess.run(
        ["git", "rev-parse", f"--short={length}", "HEAD"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def write_version(new_version: str) -> None:
    text = INIT_PATH.read_text(encoding="utf-8")
    new_text = VERSION_LINE_RE.sub(f'__version__ = "{new_version}"', text, count=1)
    INIT_PATH.write_text(new_text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sha",
        help="commit sha to embed as the local version segment (default: current HEAD)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the computed version without writing it",
    )
    args = parser.parse_args()

    current = read_current_version()
    base = next_calver(current, datetime.date.today())
    sha = args.sha or git_short_sha()
    new_version = f"{base}+{sha}"

    if not args.dry_run:
        write_version(new_version)

    print(new_version)


if __name__ == "__main__":
    main()
