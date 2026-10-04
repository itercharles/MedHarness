"""A link field holds the ID of an item that exists.

`item update` accepted `reviewed_items: ["CRS-999"]` and wrote it; only `verify dhf` later
reported "target does not exist", after the typo had reached the DHF and, in a CI run, a commit.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from medharness.cli import main
from medharness.scaffold import replace_placeholders, scaffold_dhf


@pytest.fixture
def dhf(tmp_path: Path) -> Path:
    scaffold_dhf(tmp_path)
    replace_placeholders(tmp_path, "Links")
    return tmp_path / "DHF"


def _item(dhf: Path, *args: str):
    return CliRunner().invoke(main, ["--dhf", str(dhf), "item", *args])


def _files(dhf: Path) -> set[str]:
    return {p.name for p in (dhf / "items").rglob("*.yaml")}


def test_an_update_naming_an_item_that_does_not_exist_is_refused(dhf: Path) -> None:
    before = (next((dhf / "items").rglob("CR-001.yaml"))).read_text()

    result = _item(dhf, "update", "CR-001", "--data", json.dumps({"reviewed_items": ["CRS-999"]}))

    assert result.exit_code != 0
    assert "reviewed_items: 'CRS-999' does not exist" in result.output + (result.stderr or "")
    assert next((dhf / "items").rglob("CR-001.yaml")).read_text() == before


def test_a_create_naming_an_item_that_does_not_exist_writes_nothing(dhf: Path) -> None:
    before = _files(dhf)

    result = _item(dhf, "create", "--type", "SRS", "--data", json.dumps({
        "title": "T", "content": "c", "derives_from": ["SYS-999"],
        "verification_method": ["Test"], "verification_criteria": "x", "testing": "T1: x"}))

    assert result.exit_code != 0
    assert "derives_from: 'SYS-999' does not exist" in result.output + (result.stderr or "")
    assert _files(dhf) == before


def test_a_link_to_an_item_that_exists_is_written(dhf: Path) -> None:
    result = _item(dhf, "update", "CR-001", "--data", json.dumps({"reviewed_items": ["SYS-001"]}))
    assert result.exit_code == 0, result.output


def test_an_update_that_leaves_an_old_dangling_link_alone_still_goes_through(dhf: Path) -> None:
    path = next((dhf / "items").rglob("CR-001.yaml"))
    path.write_text(path.read_text() + "reviewed_items:\n- CRS-999\n")

    result = _item(dhf, "update", "CR-001", "--data", json.dumps({"description": "Reworded."}))

    assert result.exit_code == 0, result.output
