#!/usr/bin/env python3
"""Validate release tag, package metadata, and changelog consistency."""

from pathlib import Path
import re
import sys
import tomllib

TAG_PATTERN = re.compile(
    r"^v(?P<base>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\."
    r"(?P<patch>0|[1-9]\d*)(?:-(?P<stage>alpha|beta|rc)(?P<number>[1-9]\d*))?$"
)
STAGE_MAP = {"alpha": "a", "beta": "b", "rc": "rc"}


def expected_python_version(match: re.Match[str]) -> str:
    version = f"{match['base']}.{match['minor']}.{match['patch']}"
    if match["stage"]:
        version += f"{STAGE_MAP[match['stage']]}{match['number']}"
    return version


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: check_release.py vMAJOR.MINOR.PATCH[-alphaN|-betaN|-rcN]", file=sys.stderr)
        return 2

    release_tag = sys.argv[1]
    match = TAG_PATTERN.fullmatch(release_tag)
    if not match:
        print(f"invalid release tag: {release_tag}", file=sys.stderr)
        return 1

    metadata = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    actual_version = metadata["project"]["version"]
    expected_version = expected_python_version(match)
    if actual_version != expected_version:
        print(
            f"pyproject.toml version is {actual_version}; "
            f"{release_tag} requires {expected_version}",
            file=sys.stderr,
        )
        return 1

    changelog_version = release_tag.removeprefix("v")
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")
    if not re.search(rf"^## \[{re.escape(changelog_version)}\](?: - \d{{4}}-\d{{2}}-\d{{2}})?$", changelog, re.MULTILINE):
        print(f"CHANGELOG.md has no section for {changelog_version}", file=sys.stderr)
        return 1

    print(f"release metadata is consistent for {release_tag} ({actual_version})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
