"""An interrupted write must not destroy the item it was replacing.

`save` opened the item file with mode `'w'`, which truncates before anything is
written. A failure part-way through `yaml.dump` — a full disk, a serialisation
error — left a half-written item that no longer loads, and in a DHF that item
is the record.

It also decided `created` vs `updated` *after* writing the file, so
`file_path.exists()` was always true and every new item was committed to git as
"Updated". The git history is the DHF's account of when an item came into
being.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

import dhfkit.api as api
from dhfkit.local_adapter import LocalDHFAdapter
from medharness.workflows.init import _replace_placeholders, _scaffold_dhf


@pytest.fixture
def dhf(tmp_path: Path) -> Path:
    _scaffold_dhf(tmp_path)
    _replace_placeholders(tmp_path, "Atomic")
    return tmp_path / "DHF"


class TestAFailedWriteLeavesTheItemIntact:
    def test_the_original_survives(self, dhf: Path) -> None:
        item = next((dhf / "items").rglob("SRS-*.yaml"))
        before = item.read_text(encoding="utf-8")
        real_dump = yaml.dump

        def fail_midway(*args, **kwargs):
            real_dump(*args, **kwargs)      # write some of it
            raise OSError("disk full")      # then fail

        with patch("dhfkit.repository.saver.yaml.dump", fail_midway):
            with pytest.raises(OSError):
                api.update_item(dhf, "SRS-001", {"title": "new"}, author="t")

        assert item.read_text(encoding="utf-8") == before, "the item was truncated"

    def test_the_dhf_still_loads(self, dhf: Path) -> None:
        real_dump = yaml.dump

        def fail_midway(*args, **kwargs):
            real_dump(*args, **kwargs)
            raise OSError("disk full")

        with patch("dhfkit.repository.saver.yaml.dump", fail_midway):
            with pytest.raises(OSError):
                api.update_item(dhf, "SRS-001", {"title": "new"}, author="t")

        assert api.list_items(dhf), "the DHF no longer loads after a failed write"

    def test_no_temporary_file_is_left_behind(self, dhf: Path) -> None:
        real_dump = yaml.dump

        def fail_midway(*args, **kwargs):
            real_dump(*args, **kwargs)
            raise OSError("disk full")

        with patch("dhfkit.repository.saver.yaml.dump", fail_midway):
            with pytest.raises(OSError):
                api.update_item(dhf, "SRS-001", {"title": "new"}, author="t")

        leftovers = list((dhf / "items").rglob(".*.tmp"))
        assert not leftovers, f"temporary files left behind: {leftovers}"


class TestGitRecordsCreationAsCreation:
    def _repo(self, tmp_path: Path) -> Path:
        _scaffold_dhf(tmp_path)
        _replace_placeholders(tmp_path, "Labels")
        for args in (["init", "-q"], ["add", "-A"],
                     ["-c", "user.email=t@e", "-c", "user.name=t",
                      "commit", "-qm", "scaffold"]):
            subprocess.run(["git", *args], cwd=tmp_path, capture_output=True)
        return tmp_path

    def test_a_new_item_is_committed_as_created(self, tmp_path: Path) -> None:
        root = self._repo(tmp_path)
        adapter = LocalDHFAdapter(root / "DHF", auto_commit=True)
        adapter.create_item(
            {"type": "SRS", "title": "new", "derives_from": ["SYS-001"]}, author="t"
        )
        head = subprocess.run(
            ["git", "log", "--oneline", "-1"], cwd=root,
            capture_output=True, text=True,
        ).stdout
        assert "Created" in head, f"a new item was committed as: {head.strip()}"

    def test_an_edit_is_still_committed_as_updated(self, tmp_path: Path) -> None:
        root = self._repo(tmp_path)
        adapter = LocalDHFAdapter(root / "DHF", auto_commit=True)
        created = adapter.create_item(
            {"type": "SRS", "title": "new", "derives_from": ["SYS-001"]}, author="t"
        )
        adapter.update_item(created["id"], {"title": "edited"}, author="t")
        head = subprocess.run(
            ["git", "log", "--oneline", "-1"], cwd=root,
            capture_output=True, text=True,
        ).stdout
        assert "Updated" in head, f"an edit was committed as: {head.strip()}"
