"""A new item is written beside the existing items of its type, wherever the repository keeps them.

A DHF laid out before the default directory names changed keeps `01_req_crs/`; `item create`
wrote the next CRS into a new `01_crs/`, apart from the others. IDs were allocated across both,
so nothing collided, but each type had to be moved by hand.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from medharness.cli import main
from medharness.scaffold import replace_placeholders, scaffold_dhf

CRS = {"title": "probe", "content": "x", "user_group": "u", "priority": "Low",
       "verification_method": ["Test"], "testing": "T1: x"}


@pytest.fixture
def dhf(tmp_path: Path) -> Path:
    scaffold_dhf(tmp_path)
    replace_placeholders(tmp_path, "Legacy")
    return tmp_path / "DHF"


def _create(dhf: Path, kind: str, data: dict) -> str:
    result = CliRunner().invoke(main, ["--dhf", str(dhf), "item", "create", "--type", kind, "--data", json.dumps(data)])
    assert result.exit_code == 0, result.stderr
    return json.loads(result.stdout)["id"]


def test_the_next_item_lands_in_the_directory_the_others_are_in(dhf: Path) -> None:
    (dhf / "items" / "01_crs").rename(dhf / "items" / "01_req_crs")

    uid = _create(dhf, "CRS", CRS)

    assert (dhf / "items" / "01_req_crs" / f"{uid}.yaml").is_file()
    assert not (dhf / "items" / "01_crs").exists()


def test_a_type_with_no_item_yet_goes_to_its_configured_directory(dhf: Path) -> None:
    for item in (dhf / "items" / "12_def").glob("*.yaml"):
        item.unlink()

    uid = _create(dhf, "DEF", {"title": "t", "description": "d", "severity": "Low", "priority": "Low"})

    assert (dhf / "items" / "12_def" / f"{uid}.yaml").is_file()


def test_a_longer_prefix_is_not_taken_for_its_shorter_relative(dhf: Path) -> None:
    """SYS- items must not be filed with SYSARCH- items, whose names start the same way."""
    uid = _create(dhf, "SYS", {"title": "t", "content": "c", "category": "Functional", "satisfies": ["CRS-001"]})
    assert (dhf / "items" / "02_sys" / f"{uid}.yaml").is_file()
