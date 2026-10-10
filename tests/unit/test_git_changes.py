"""Unit tests for medharness.services.git change-collection helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from medharness.services.git import DiffUnavailable, collect_dhf_item_changes, collect_path_changes


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
        with patch("subprocess.run", side_effect=[_completed("base\n", 0), _completed(diff, 0), _completed("", 0)]):
            result = collect_path_changes(tmp_path, "origin/main", "apps/")
        assert result == {
            "created": ["apps/client/src/added.ts"],
            "updated": ["apps/client/src/modified.ts"],
            "deleted": ["apps/client/src/deleted.ts"],
        }

    def test_rename_counted_as_update_on_new_path(self, tmp_path: Path):
        diff = "R100\tapps/old.ts\tapps/new.ts\n"
        with patch("subprocess.run", side_effect=[_completed("base\n", 0), _completed(diff, 0), _completed("", 0)]):
            result = collect_path_changes(tmp_path, "origin/main", "apps/")
        assert result == {"created": [], "updated": ["apps/new.ts"], "deleted": []}

    def test_git_unavailable_is_not_an_empty_diff(self, tmp_path: Path):
        with patch("subprocess.run", side_effect=FileNotFoundError), \
             pytest.raises(DiffUnavailable, match="not installed"):
            collect_path_changes(tmp_path, "origin/main", "apps/")

    def test_a_failed_diff_says_why(self, tmp_path: Path):
        """An unfetched ref was three empty lists — the same as a branch that changed nothing."""
        failed = _completed("", 128)
        failed.stderr = "fatal: bad revision 'origin/main'\n"
        with patch("subprocess.run", return_value=failed), \
             pytest.raises(DiffUnavailable, match="bad revision 'origin/main'"):
            collect_path_changes(tmp_path, "origin/main", "apps/")


class TestCollectDhfItemChanges:
    def test_extracts_ids_and_skips_non_yaml(self, tmp_path: Path):
        diff = (
            "A\tDHF/items/01_sys/SYS-001.yaml\n"
            "M\tDHF/items/02_srs/SRS-002.yaml\n"
            "D\tDHF/items/02_srs/SRS-099.yaml\n"
            "M\tDHF/items/02_srs/README.md\n"     # non-yaml — skipped
        )
        with patch("subprocess.run", side_effect=[_completed("base\n", 0), _completed(diff, 0), _completed("", 0)]):
            result = collect_dhf_item_changes(tmp_path, "origin/main")
        assert result == {
            "created": ["SYS-001"],
            "updated": ["SRS-002"],
            "deleted": ["SRS-099"],
        }


class TestARealRepository:
    def test_a_path_with_non_ascii_characters_is_reported_as_it_is_named(self, tmp_path: Path):
        """git writes such a path quoted and octal-escaped unless told not to; the escaped
        string names no file, and it is what `artifacts.files_changed` showed."""
        import subprocess

        def git(*args: str) -> None:
            subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True)

        git("init", "-q", "-b", "main")
        git("config", "user.email", "t@example.com")
        git("config", "user.name", "t")
        (tmp_path / "base.txt").write_text("x")
        git("add", "-A")
        git("commit", "-qm", "base")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "文档.py").write_text("x = 1\n", encoding="utf-8")
        (tmp_path / "base.txt").write_text("y")
        (tmp_path / "文档.md").write_text("z", encoding="utf-8")
        git("add", "文档.md")

        changed = collect_path_changes(tmp_path, "main", "src/", "文档.md", "base.txt")

        assert sorted(changed["created"]) == ["src/文档.py", "文档.md"]
        assert changed["updated"] == ["base.txt"]
