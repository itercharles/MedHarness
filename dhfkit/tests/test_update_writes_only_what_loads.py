"""`item update` refuses a value the schema would reject on the next read.

It wrote `verification_method: Test` where the doc type wants a list. The next
read failed on that file, and so did every command after it — including the
`item update` that would have corrected it.
"""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from dhfkit.cli import main
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
    assert "must be a list" in r.output
    assert item.read_bytes() == before
    assert CliRunner().invoke(main, ["--dhf", str(dhf), "validate"]).exit_code == 0


def test_the_right_shape_is_written(tmp_path: Path) -> None:
    dhf = _dhf(tmp_path)
    r = CliRunner().invoke(main, ["--dhf", str(dhf), "item", "update", "CRS-001",
                                  "--data", '{"verification_method": ["Test"]}'])
    assert r.exit_code == 0, r.output
    assert CliRunner().invoke(main, ["--dhf", str(dhf), "validate"]).exit_code == 0
