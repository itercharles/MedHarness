"""An update rewrites the file the item was read from.

The saver always wrote to the doc type's configured directory, so an item kept
elsewhere — a DHF laid out before the default directories changed, `09_cr/`
where the default is `07_cr/` — gained a second file with the same ID on its
first update, and the schema check failed on the duplicate.
"""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from medharness.cli import main
from dhfkit.local_adapter import LocalDHFAdapter
from dhfkit.tests.fixtures import bare_dhf


def _dhf_with_a_cr_in_a_legacy_directory(tmp_path: Path) -> Path:
    dhf = tmp_path / "DHF"
    bare_dhf(dhf)
    legacy = dhf / "items" / "09_cr"
    legacy.mkdir(parents=True)
    (legacy / "CR-001.yaml").write_text('id: CR-001\ntitle: "A change"\nstatus: new\n')
    return dhf


def _copies(dhf: Path, uid: str) -> list[str]:
    return sorted(str(p.relative_to(dhf)) for p in (dhf / "items").rglob(f"{uid}.yaml"))


def test_update_rewrites_the_file_in_place(tmp_path: Path) -> None:
    dhf = _dhf_with_a_cr_in_a_legacy_directory(tmp_path)

    LocalDHFAdapter(dhf).update_item("CR-001", {"affected_items": []})

    assert _copies(dhf, "CR-001") == ["items/09_cr/CR-001.yaml"]
    assert "affected_items" in (dhf / "items" / "09_cr" / "CR-001.yaml").read_text()


def test_transition_rewrites_the_file_in_place(tmp_path: Path) -> None:
    dhf = _dhf_with_a_cr_in_a_legacy_directory(tmp_path)

    result = CliRunner().invoke(main, ["--dhf", str(dhf), "item", "transition", "CR-001", "design"])

    assert result.exit_code == 0, result.output
    assert _copies(dhf, "CR-001") == ["items/09_cr/CR-001.yaml"]
    assert "status: design" in (dhf / "items" / "09_cr" / "CR-001.yaml").read_text()
    assert LocalDHFAdapter(dhf).validate_schema()["valid"]


def test_a_new_item_goes_to_its_doc_types_directory(tmp_path: Path) -> None:
    """The other half: with no file yet, the configured directory decides."""
    dhf = _dhf_with_a_cr_in_a_legacy_directory(tmp_path)

    created = LocalDHFAdapter(dhf).create_item({"type": "CR", "title": "Another change"})

    assert _copies(dhf, created["id"]) == [f"items/07_cr/{created['id']}.yaml"]
