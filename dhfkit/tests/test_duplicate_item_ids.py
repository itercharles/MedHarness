"""Two files claiming one ID make every reference to it ambiguous.

An ID is what the rest of the DHF points at — `dhf_links`, `affected_items`, an
approval's scope, a test's evidence. With two items answering to SRS-001,
`get_item` returns whichever the loader saw first and the other exists,
unreferenced and unreachable.

Nothing reported it. Each file was individually schema-valid, `validate`
counted them separately and passed, and `verify dhf` returned `passed: true`.
The only visible symptom was one traceability warning printed twice — which
reads as a rendering glitch, not as a second item.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

import dhfkit.api as api
from dhfkit.local_adapter import LocalDHFAdapter
from medharness.workflows.init import _replace_placeholders, _scaffold_dhf


@pytest.fixture
def dhf(tmp_path: Path) -> Path:
    _scaffold_dhf(tmp_path)
    _replace_placeholders(tmp_path, "Duplicates")
    return tmp_path / "DHF"


def _duplicate(dhf: Path, item_id: str, new_name: str) -> Path:
    source = next((dhf / "items").rglob(f"{item_id}.yaml"))
    copy = source.parent / new_name
    copy.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    return copy


class TestDuplicatesAreReported:
    def test_validate_schema_names_both_files(self, dhf: Path) -> None:
        _duplicate(dhf, "SRS-001", "SRS-001-copy.yaml")
        result = LocalDHFAdapter(dhf).validate_schema()
        assert not result["valid"]
        assert "Duplicate item ID 'SRS-001'" in " ".join(result["errors"])
        assert "SRS-001.yaml" in " ".join(result["errors"])
        assert "SRS-001-copy.yaml" in " ".join(result["errors"])

    def test_verify_dhf_fails(self, dhf: Path) -> None:
        """The gate is where CI finds out."""
        _duplicate(dhf, "SRS-001", "SRS-001-copy.yaml")
        proc = subprocess.run(
            [sys.executable, "-m", "medharness", "--dhf", str(dhf), "verify", "dhf"],
            capture_output=True, text=True,
        )
        assert proc.returncode == 1
        payload = json.loads(proc.stdout.splitlines()[0])
        assert payload["passed"] is False
        assert any("Duplicate item ID" in e for e in payload["errors"])

    def test_a_differing_copy_is_reported_too(self, dhf: Path) -> None:
        """The dangerous case: two items with one ID and different content."""
        copy = _duplicate(dhf, "SRS-001", "SRS-001-alt.yaml")
        copy.write_text(
            copy.read_text(encoding="utf-8").replace("title:", "title: Divergent —", 1),
            encoding="utf-8",
        )
        result = LocalDHFAdapter(dhf).validate_schema()
        assert not result["valid"]
        assert "Duplicate item ID 'SRS-001'" in " ".join(result["errors"])

    def test_the_filename_is_not_what_makes_it_a_duplicate(self, dhf: Path) -> None:
        """The id inside the file is authoritative; the name is not.

        A copy renamed to something unrelated is still a duplicate, and a file
        whose name matches nothing is fine as long as its id is unique.
        """
        _duplicate(dhf, "SRS-001", "notes-about-srs.yaml")
        result = LocalDHFAdapter(dhf).validate_schema()
        assert not result["valid"]
        assert "notes-about-srs.yaml" in " ".join(result["errors"])


class TestAHealthyDhfIsUnaffected:
    def test_the_scaffold_passes(self, dhf: Path) -> None:
        result = LocalDHFAdapter(dhf).validate_schema()
        assert result["valid"], result["errors"]

    def test_the_item_count_is_still_reported(self, dhf: Path) -> None:
        result = LocalDHFAdapter(dhf).validate_schema()
        assert result["item_count"] > 0

    def test_a_renamed_file_with_a_unique_id_is_fine(self, dhf: Path) -> None:
        source = next((dhf / "items").rglob("SRS-001.yaml"))
        renamed = source.parent / "some-other-name.yaml"
        source.rename(renamed)
        result = LocalDHFAdapter(dhf).validate_schema()
        assert result["valid"], result["errors"]
        assert api.get_item(dhf, "SRS-001") is not None

    def test_an_unparseable_file_is_left_to_the_loader(self, dhf: Path) -> None:
        """The duplicate scan must not become a second YAML error reporter."""
        (dhf / "items" / "03_srs" / "broken.yaml").write_text("{[not yaml", encoding="utf-8")
        result = LocalDHFAdapter(dhf).validate_schema()
        assert "Duplicate" not in " ".join(result["errors"])
