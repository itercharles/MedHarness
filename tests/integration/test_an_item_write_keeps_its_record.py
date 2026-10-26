"""`item create` and `item update` write a record that stays the same record: links that resolve, an ID
that is the item's for good, and an approved item that is not edited unnoticed."""

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
    replace_placeholders(tmp_path, "Writes")
    return tmp_path / "DHF"


def _item(dhf: Path, *args: str):
    return CliRunner().invoke(main, ["--dhf", str(dhf), "item", *args])


def _files(dhf: Path) -> list[Path]:
    return sorted((dhf / "items").rglob("*.yaml"))


@pytest.mark.dhf_links("SRS-056")
@pytest.mark.dhf_testing("T3")
def test_a_link_to_an_item_that_does_not_exist_is_refused(dhf: Path) -> None:
    before = _files(dhf)

    result = _item(dhf, "create", "--type", "SRS", "--data", json.dumps({"title": "t", "derives_from": ["SYS-999"]}))

    assert result.exit_code == 1 and result.stdout == ""
    assert "derives_from: 'SYS-999' does not exist" in result.stderr
    assert _files(dhf) == before


@pytest.mark.dhf_links("SRS-057")
@pytest.mark.dhf_testing("T4")
def test_an_update_cannot_change_the_id(dhf: Path) -> None:
    path = next((dhf / "items").rglob("SRS-001.yaml"))
    before = path.read_bytes()

    result = _item(dhf, "update", "SRS-001", "--data", '{"id": "SRS-777"}')

    assert result.exit_code == 1 and "immutable" in result.stderr
    assert path.read_bytes() == before
    assert not list((dhf / "items").rglob("SRS-777.yaml"))


@pytest.mark.dhf_links("SRS-057")
@pytest.mark.dhf_testing("T6")
def test_editing_an_item_in_a_stable_state_returns_it_to_its_initial_state(dhf: Path) -> None:
    assert json.loads(_item(dhf, "get", "DEF-001").stdout)["status"] == "closed"

    result = _item(dhf, "update", "DEF-001", "--data", '{"title": "Edited after it was closed"}')

    assert result.exit_code == 0, result.stderr
    assert json.loads(_item(dhf, "get", "DEF-001").stdout)["status"] == "draft"


@pytest.mark.dhf_links("SRS-059")
@pytest.mark.dhf_testing("T3")
def test_an_id_the_caller_gives_is_not_used(dhf: Path) -> None:
    result = _item(dhf, "create", "--type", "SRS",
                   "--data", json.dumps({"id": "SRS-500", "title": "t", "derives_from": ["SYS-001"]}))

    assert result.exit_code == 0, result.stderr
    assert json.loads(result.stdout)["id"] == "SRS-002"
    assert not list((dhf / "items").rglob("SRS-500.yaml"))
