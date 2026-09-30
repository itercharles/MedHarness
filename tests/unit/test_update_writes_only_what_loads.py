"""`item update` refuses a value the schema would reject on the next read.

It wrote `verification_method: Test` where the doc type wants a list. The next
read failed on that file, and so did every command after it — including the
`item update` that would have corrected it.
"""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from dhfkit.item_store import ItemStore
from medharness.cli import main
from dhfkit.tests.fixtures import bare_dhf


def _dhf(tmp_path: Path) -> Path:
    dhf = bare_dhf(tmp_path / "DHF")
    (dhf / "items" / "01_crs" / "CRS-001.yaml").write_text("id: CRS-001\ntitle: A need\n")
    return dhf


def test_a_value_of_the_wrong_shape_is_refused_and_nothing_is_written(tmp_path: Path) -> None:
    dhf = _dhf(tmp_path)
    item = dhf / "items" / "01_crs" / "CRS-001.yaml"
    before = item.read_bytes()

    r = CliRunner().invoke(main, ["--dhf", str(dhf), "item", "update", "CRS-001",
                                  "--data", '{"verification_method": "Test"}'])

    assert r.exit_code != 0
    assert "CRS-001 not updated" in r.output and "must be a list" in r.output
    assert "could not be read" not in r.output, "the DHF is fine; the write was refused"
    assert item.read_bytes() == before
    assert ItemStore(dhf).validate_schema()["valid"]


def test_the_right_shape_is_written(tmp_path: Path) -> None:
    dhf = _dhf(tmp_path)
    r = CliRunner().invoke(main, ["--dhf", str(dhf), "item", "update", "CRS-001",
                                  "--data", '{"verification_method": ["Test"]}'])
    assert r.exit_code == 0, r.output
    assert ItemStore(dhf).validate_schema()["valid"]
