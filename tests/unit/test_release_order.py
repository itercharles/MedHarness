"""A release is compared with the latest release numbered below it, by number rather than by text."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from medharness.services.release_manifest import previous_manifest


def _write(dhf: Path, version: str) -> None:
    folder = dhf / "releases" / version
    folder.mkdir(parents=True)
    (folder / "manifest.yaml").write_text(yaml.safe_dump({"version": version, "dhf_hash": "sha256:x", "documents": {}}))


@pytest.mark.parametrize(("version", "expected"), [
    ("1.10.0", "1.9.0"),
    ("1.9.0", "1.2.0"),
    ("1.2.0", "1.1.0"),
    ("1.1.0", None),
    ("2.0.0", "1.10.0"),
    ("1.9.1", "1.9.0"),
    ("nightly", None),
])
def test_the_previous_release_is_the_next_lower_version_number(tmp_path: Path, version: str, expected: str | None) -> None:
    for existing in ("1.1.0", "1.2.0", "1.9.0", "1.10.0"):
        _write(tmp_path, existing)

    previous = previous_manifest(tmp_path, version)

    assert (previous["version"] if previous else None) == expected


def test_a_release_with_no_releases_before_it_has_no_previous(tmp_path: Path) -> None:
    assert previous_manifest(tmp_path, "1.0.0") is None
