"""Tests for atomic branch validation."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from medharness.services.git import validate_atomic_branch


def test_validate_atomic_branch_passes_when_code_and_dhf_are_present(tmp_path: Path):
    repo_root = tmp_path
    dhf = repo_root / "DHF"
    dhf.mkdir()

    with patch("medharness.services.git.collect_dhf_item_changes") as mock_items:
        mock_items.return_value = {"created": ["SRS-010"], "updated": ["SYS-001"], "deleted": []}
        result = validate_atomic_branch(repo_root, dhf, "CR-001")

    assert result["passed"] is True
    assert result["details"]["findings"] == []
    assert result["details"]["cr_found"] in (True, False)


def test_validate_atomic_branch_fails_without_code_changes(tmp_path: Path):
    repo_root = tmp_path
    dhf = repo_root / "DHF"
    dhf.mkdir()

    with patch("medharness.services.git.collect_path_changes") as mock_paths, \
         patch("medharness.services.git.collect_dhf_item_changes", return_value={"created": [], "updated": [], "deleted": []}):
        mock_paths.return_value = {"created": [], "updated": [], "deleted": []}
        # code_paths must be explicit — the default () skips the code-change check
        result = validate_atomic_branch(repo_root, dhf, "CR-001", code_paths=("src/",))

    assert result["passed"] is False
    assert any(e["field"] == "code_branch" for e in result["details"]["findings"])


def test_validate_atomic_branch_passes_when_dhf_changes_present(tmp_path: Path):
    """DHF changes are required and sufficient to pass."""
    repo_root = tmp_path
    dhf = repo_root / "DHF"
    dhf.mkdir()

    with patch("medharness.services.git.collect_dhf_item_changes",
               return_value={"created": ["SRS-010"], "updated": [], "deleted": []}):
        result = validate_atomic_branch(repo_root, dhf, "CR-001")

    assert result["passed"] is True
    assert result["details"]["findings"] == []
    assert "spec_path" not in result


def test_a_cr_with_nothing_promised_and_nothing_changed_fails(tmp_path: Path):
    """The old rule was "every CR branch must change the DHF". That fails any PR
    with no CR, which is why adopters had to guard this command with workflow
    conditions. It now checks the CR's own affected_items; the blanket case
    survives only when a CR exists and promised nothing."""
    repo_root = tmp_path
    dhf = repo_root / "DHF"
    dhf.mkdir()

    with patch("medharness.services.git.collect_dhf_item_changes",
               return_value={"created": [], "updated": [], "deleted": []}), \
         patch("dhfkit.local_adapter.LocalDHFAdapter") as adapter:
        adapter.return_value.get_item.return_value = {"id": "CR-001", "affected_items": []}
        result = validate_atomic_branch(repo_root, dhf, "CR-001")

    assert result["passed"] is False
    assert any(e["field"] == "dhf_branch" for e in result["details"]["findings"])




