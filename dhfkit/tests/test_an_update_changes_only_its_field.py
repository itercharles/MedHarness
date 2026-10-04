"""A one-field update shows as one field in the diff.

Items are controlled records reviewed as diffs. `item update` used to re-dump
the whole file, so pinning one version re-quoted, re-wrapped and re-blocked
twenty lines, and the reviewer could not see what changed.
"""

from __future__ import annotations

import difflib
from pathlib import Path

from dhfkit.store import open_store
from dhfkit.tests.fixtures import bare_dhf

HAND_WRITTEN = '''id: SRS-001
title: "A requirement"
content: |-
  First line of a literal block.
  Second line, kept as written.
performance: A plain scalar long enough that a dumper would wrap it somewhere past
  the eightieth column.
verification_method:
  - Test
  - Inspection
'''


def _changed_lines(before: str, after: str) -> list[str]:
    return [line for line in difflib.unified_diff(before.splitlines(), after.splitlines(), lineterm="", n=0)
            if line[:1] in "+-" and not line.startswith(("+++", "---"))]


def _item(tmp_path: Path) -> tuple[Path, Path]:
    dhf = bare_dhf(tmp_path / "DHF")
    path = dhf / "items" / "03_srs" / "SRS-001.yaml"
    path.write_text(HAND_WRITTEN, encoding="utf-8")
    return dhf, path


def test_only_the_changed_line_differs(tmp_path: Path) -> None:
    dhf, path = _item(tmp_path)
    open_store(dhf).update_item("SRS-001", {"title": "A clearer requirement"})
    assert _changed_lines(HAND_WRITTEN, path.read_text(encoding="utf-8")) == [
        '-title: "A requirement"', '+title: A clearer requirement']


def test_a_new_field_is_one_added_line(tmp_path: Path) -> None:
    dhf, path = _item(tmp_path)
    open_store(dhf).update_item("SRS-001", {"testing": "Unit"})
    assert _changed_lines(HAND_WRITTEN, path.read_text(encoding="utf-8")) == ["+testing: Unit"]


def test_a_cleared_field_is_one_removed_line(tmp_path: Path) -> None:
    dhf, path = _item(tmp_path)
    open_store(dhf).update_item("SRS-001", {"performance": None})
    changed = _changed_lines(HAND_WRITTEN, path.read_text(encoding="utf-8"))
    assert all(line.startswith("-") for line in changed) and len(changed) == 2
    assert open_store(dhf).get_item("SRS-001").get("performance") is None


def test_a_file_without_a_final_newline_gets_its_field_on_its_own_line(tmp_path: Path) -> None:
    dhf, path = _item(tmp_path)
    path.write_text(HAND_WRITTEN.rstrip("\n"), encoding="utf-8")
    open_store(dhf).update_item("SRS-001", {"testing": "Unit"})
    assert open_store(dhf).get_item("SRS-001")["verification_method"] == ["Test", "Inspection"]
    assert path.read_text(encoding="utf-8").endswith("  - Inspection\ntesting: Unit\n")
