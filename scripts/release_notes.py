#!/usr/bin/env python3
"""Print the changelog body for a release tag."""

from pathlib import Path
import re
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: release_notes.py vMAJOR.MINOR.PATCH[-PRERELEASE]", file=sys.stderr)
        return 2

    version = sys.argv[1].removeprefix("v")
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")
    section = re.search(
        rf"^## \[{re.escape(version)}\](?: - \d{{4}}-\d{{2}}-\d{{2}})?\n"
        r"(?P<body>.*?)(?=^## \[|^\[Unreleased\]:|\Z)",
        changelog,
        re.MULTILINE | re.DOTALL,
    )
    if not section:
        print(f"CHANGELOG.md has no section for {version}", file=sys.stderr)
        return 1

    notes = section["body"].strip()
    if not notes:
        print(f"CHANGELOG.md section for {version} is empty", file=sys.stderr)
        return 1

    print(notes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
