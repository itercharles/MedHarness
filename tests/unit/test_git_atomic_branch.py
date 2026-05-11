"""Tests for atomic branch validation."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from medharness.services.git import validate_atomic_branch


def _write_spec(path: Path, *, affected: list[str] | None = None, proposed: list[dict] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    affected = affected or []
    proposed = proposed or []
    affected_yaml = "\n".join(f"  - {uid}" for uid in affected) if affected else " []"
    if proposed:
        proposed_yaml = "\n".join(
            f"  - type: {item['type']}\n    title: \"{item['title']}\"" for item in proposed
        )
        proposed_block = f"proposed_new_items:\n{proposed_yaml}\n"
    else:
        proposed_block = "proposed_new_items: []\n"
    path.write_text(
        "---\n"
        'cr_id: "CR-001"\n'
        'direction_fit: "in-scope"\n'
        f"affected_items:{(' ' + affected_yaml.lstrip()) if not affected else chr(10) + affected_yaml}\n"
        f"{proposed_block}"
        'design_impact_summary: "summary"\n'
        "test_plan:\n"
        "  auto_covered: []\n"
        "  needs_new_tc: []\n"
        "  must_be_manual: []\n"
        "---\n",
        encoding="utf-8",
    )


def test_validate_atomic_branch_passes_when_spec_code_and_dhf_are_present(tmp_path: Path):
    repo_root = tmp_path
    dhf = repo_root / "DHF"
    dhf.mkdir()
    spec = repo_root / "docs" / "cr-specs" / "CR-001-Spec.md"
    _write_spec(spec, affected=["SYS-001"], proposed=[{"type": "SRS", "title": "New req"}])

    with patch("medharness.services.git.collect_path_changes") as mock_paths, \
         patch("medharness.services.git.collect_dhf_item_changes") as mock_items:
        mock_paths.side_effect = [
            {"created": [], "updated": ["docs/cr-specs/CR-001-Spec.md"], "deleted": []},
            {"created": ["apps/client/src/feature.ts"], "updated": [], "deleted": []},
        ]
        mock_items.return_value = {"created": ["SRS-010"], "updated": ["SYS-001"], "deleted": []}
        result = validate_atomic_branch(repo_root, dhf, "CR-001")

    assert result["passed"] is True
    assert result["errors"] == []
    assert result["expected_dhf_changes"] is True


def test_validate_atomic_branch_allows_spec_already_merged_on_main(tmp_path: Path):
    repo_root = tmp_path
    dhf = repo_root / "DHF"
    dhf.mkdir()
    spec = repo_root / "docs" / "cr-specs" / "CR-001-Spec.md"
    _write_spec(spec, affected=["SYS-001"])

    with patch("medharness.services.git.collect_path_changes") as mock_paths, \
         patch("medharness.services.git.collect_dhf_item_changes") as mock_items:
        mock_paths.side_effect = [
            {"created": [], "updated": [], "deleted": []},
            {"created": ["apps/client/src/feature.ts"], "updated": [], "deleted": []},
        ]
        mock_items.return_value = {"created": [], "updated": ["SYS-001"], "deleted": []}
        result = validate_atomic_branch(repo_root, dhf, "CR-001")

    assert result["passed"] is True
    assert result["errors"] == []
    assert result["spec_changes"] == {"created": [], "updated": [], "deleted": []}


def test_validate_atomic_branch_fails_without_code_changes(tmp_path: Path):
    repo_root = tmp_path
    dhf = repo_root / "DHF"
    dhf.mkdir()
    spec = repo_root / "docs" / "cr-specs" / "CR-001-Spec.md"
    _write_spec(spec)

    with patch("medharness.services.git.collect_path_changes") as mock_paths, \
         patch("medharness.services.git.collect_dhf_item_changes", return_value={"created": [], "updated": [], "deleted": []}):
        mock_paths.side_effect = [
            {"created": [], "updated": ["docs/cr-specs/CR-001-Spec.md"], "deleted": []},
            {"created": [], "updated": [], "deleted": []},
        ]
        result = validate_atomic_branch(repo_root, dhf, "CR-001")

    assert result["passed"] is False
    assert any(e["field"] == "code_branch" for e in result["errors"])


def test_validate_atomic_branch_fails_when_spec_is_missing(tmp_path: Path):
    repo_root = tmp_path
    dhf = repo_root / "DHF"
    dhf.mkdir()

    with patch("medharness.services.git.collect_path_changes") as mock_paths, \
         patch("medharness.services.git.collect_dhf_item_changes", return_value={"created": [], "updated": [], "deleted": []}):
        mock_paths.side_effect = [
            {"created": [], "updated": [], "deleted": []},
            {"created": ["apps/client/src/feature.ts"], "updated": [], "deleted": []},
        ]
        result = validate_atomic_branch(repo_root, dhf, "CR-001")

    assert result["passed"] is False
    assert any(e["field"] == "spec_path" for e in result["errors"])


def test_validate_atomic_branch_fails_without_dhf_changes_when_spec_expects_them(tmp_path: Path):
    repo_root = tmp_path
    dhf = repo_root / "DHF"
    dhf.mkdir()
    spec = repo_root / "docs" / "cr-specs" / "CR-001-Spec.md"
    _write_spec(spec, proposed=[{"type": "SRS", "title": "New req"}])

    with patch("medharness.services.git.collect_path_changes") as mock_paths, \
         patch("medharness.services.git.collect_dhf_item_changes", return_value={"created": [], "updated": [], "deleted": []}):
        mock_paths.side_effect = [
            {"created": [], "updated": ["docs/cr-specs/CR-001-Spec.md"], "deleted": []},
            {"created": ["apps/client/src/feature.ts"], "updated": [], "deleted": []},
        ]
        result = validate_atomic_branch(repo_root, dhf, "CR-001")

    assert result["passed"] is False
    assert any(e["field"] == "dhf_branch" for e in result["errors"])
