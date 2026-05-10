"""Unit tests for medharness.services.git change-collection helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from medharness.services.git import collect_dhf_item_changes, collect_path_changes


def _completed(stdout: str = "", returncode: int = 0) -> MagicMock:
    return MagicMock(stdout=stdout, returncode=returncode)


class TestCollectPathChanges:
    def test_empty_diff_returns_empty_buckets(self, tmp_path: Path):
        with patch("subprocess.run", return_value=_completed("", 0)):
            result = collect_path_changes(tmp_path, "origin/main", "apps/")
        assert result == {"created": [], "updated": [], "deleted": []}

    def test_classifies_status_codes(self, tmp_path: Path):
        diff = (
            "A\tapps/client/src/added.ts\n"
            "M\tapps/client/src/modified.ts\n"
            "D\tapps/client/src/deleted.ts\n"
        )
        with patch("subprocess.run", return_value=_completed(diff, 0)):
            result = collect_path_changes(tmp_path, "origin/main", "apps/")
        assert result == {
            "created": ["apps/client/src/added.ts"],
            "updated": ["apps/client/src/modified.ts"],
            "deleted": ["apps/client/src/deleted.ts"],
        }

    def test_rename_counted_as_update_on_new_path(self, tmp_path: Path):
        diff = "R100\tapps/old.ts\tapps/new.ts\n"
        with patch("subprocess.run", return_value=_completed(diff, 0)):
            result = collect_path_changes(tmp_path, "origin/main", "apps/")
        assert result == {"created": [], "updated": ["apps/new.ts"], "deleted": []}

    def test_git_unavailable_returns_empty(self, tmp_path: Path):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = collect_path_changes(tmp_path, "origin/main", "apps/")
        assert result == {"created": [], "updated": [], "deleted": []}

    def test_nonzero_exit_returns_empty(self, tmp_path: Path):
        with patch("subprocess.run", return_value=_completed("", 128)):
            result = collect_path_changes(tmp_path, "origin/main", "apps/")
        assert result == {"created": [], "updated": [], "deleted": []}


class TestCollectDhfItemChanges:
    def test_extracts_ids_and_skips_non_yaml(self, tmp_path: Path):
        diff = (
            "A\tDHF/items/01_sys/SYS-001.yaml\n"
            "M\tDHF/items/02_srs/SRS-002.yaml\n"
            "D\tDHF/items/02_srs/SRS-099.yaml\n"
            "M\tDHF/items/02_srs/README.md\n"     # non-yaml — skipped
        )
        with patch("subprocess.run", return_value=_completed(diff, 0)):
            result = collect_dhf_item_changes(tmp_path, "origin/main")
        assert result == {
            "created": ["SYS-001"],
            "updated": ["SRS-002"],
            "deleted": ["SRS-099"],
        }
