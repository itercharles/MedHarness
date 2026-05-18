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
    assert result["errors"] == []
    assert result["expected_dhf_changes"] is True


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
    assert any(e["field"] == "code_branch" for e in result["errors"])


def test_validate_atomic_branch_passes_when_dhf_changes_present(tmp_path: Path):
    """DHF changes are required and sufficient to pass."""
    repo_root = tmp_path
    dhf = repo_root / "DHF"
    dhf.mkdir()

    with patch("medharness.services.git.collect_dhf_item_changes",
               return_value={"created": ["SRS-010"], "updated": [], "deleted": []}):
        result = validate_atomic_branch(repo_root, dhf, "CR-001")

    assert result["passed"] is True
    assert result["errors"] == []
    assert "spec_path" not in result


def test_validate_atomic_branch_fails_without_dhf_changes(tmp_path: Path):
    """DHF changes are always required (generate-dhf must run on every CR branch)."""
    repo_root = tmp_path
    dhf = repo_root / "DHF"
    dhf.mkdir()

    with patch("medharness.services.git.collect_dhf_item_changes",
               return_value={"created": [], "updated": [], "deleted": []}):
        result = validate_atomic_branch(repo_root, dhf, "CR-001")

    assert result["passed"] is False
    assert any(e["field"] == "dhf_branch" for e in result["errors"])


def test_validate_atomic_branch_includes_risk_impact(tmp_path: Path):
    """risk_impact is populated from find_affected_risks when DHF is loadable."""
    repo_root = tmp_path
    dhf = repo_root / "DHF"
    dhf.mkdir()

    mock_adapter = MagicMock()
    mock_adapter.list_items.return_value = []
    mock_adapter._config = MagicMock()

    expected_impact = [{"risk_id": "RISK-001", "title": "Dose error", "via_rcms": ["RCM-001"]}]

    with patch("medharness.services.git.collect_dhf_item_changes",
               return_value={"created": ["SYS-010"], "updated": [], "deleted": []}), \
         patch("dhfkit.local_adapter.LocalDHFAdapter", return_value=mock_adapter), \
         patch("dhfkit.traceability.find_affected_risks", return_value=expected_impact):
        result = validate_atomic_branch(repo_root, dhf, "CR-001")

    assert result["passed"] is True
    assert result["risk_impact"] == expected_impact


def test_validate_atomic_branch_risk_impact_empty_when_dhf_not_loadable(tmp_path: Path):
    """risk_impact is [] when the DHF directory is missing (graceful degradation)."""
    repo_root = tmp_path
    dhf = repo_root / "DHF"  # directory not created

    with patch("medharness.services.git.collect_dhf_item_changes",
               return_value={"created": ["SYS-010"], "updated": [], "deleted": []}):
        result = validate_atomic_branch(repo_root, dhf, "CR-001")

    assert result["passed"] is True
    assert result["risk_impact"] == []
