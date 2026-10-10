"""A relationship field may hold one ID instead of a list; it is one link, not one per character.

The loader accepts `derives_from: SYS-001`. The dangling-link check iterated the
string, so every character of a valid ID was reported as a missing target.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from click.testing import CliRunner

from medharness.cli import main
from medharness.scaffold import replace_placeholders, scaffold_dhf


def _derive_srs_from(dhf: Path, target: str) -> None:
    """Write SRS-001's `derives_from` as one bare ID, which the loader accepts."""
    path = next((dhf / "items").rglob("SRS-001.yaml"))
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["derives_from"] = target
    path.write_text(yaml.safe_dump(data), encoding="utf-8")


def _verify(dhf: Path) -> dict:
    return json.loads(CliRunner().invoke(main, ["--dhf", str(dhf), "verify", "dhf"]).stdout)


def test_a_single_id_that_exists_is_no_dangling_link(tmp_path: Path) -> None:
    scaffold_dhf(tmp_path)
    replace_placeholders(tmp_path, "One")
    dhf = tmp_path / "DHF"
    _derive_srs_from(dhf, "SYS-001")

    assert not [e for e in _verify(dhf)["errors"] if "target does not exist" in e]


def test_a_single_id_that_does_not_exist_is_one_dangling_link(tmp_path: Path) -> None:
    scaffold_dhf(tmp_path)
    replace_placeholders(tmp_path, "One")
    dhf = tmp_path / "DHF"
    _derive_srs_from(dhf, "SYS-999")

    dangling = [e for e in _verify(dhf)["errors"] if "target does not exist" in e]
    assert dangling == ["SRS-001.derives_from → SYS-999: target does not exist"]
