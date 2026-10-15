"""The version in pyproject.toml has a CHANGELOG entry, and uv.lock records the same version.

The release workflow refuses a tag whose version has no changelog entry or does not match
pyproject.toml, but only once the tag is pushed, after the pull request has merged. Twice a
version bump reached `main` without its entry; this fails the pull request instead.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _version() -> str:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]


def test_the_current_version_has_a_changelog_entry() -> None:
    assert f"## [{_version()}]" in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"), (
        f"CHANGELOG.md has no '## [{_version()}]' entry"
    )


def test_the_lockfile_records_the_current_version() -> None:
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    recorded = next(p["version"] for p in lock["package"] if p["name"] == "medharness")
    assert recorded == _version(), f"uv.lock records {recorded}; run `uv lock`"
