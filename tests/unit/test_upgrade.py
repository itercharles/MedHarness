"""Tests for medharness upgrade command."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from medharness.cli import main
from medharness.workflows.upgrade import apply_upgrade, check_upgrade, _UPGRADE_MAP, _TEMPLATES_DIR


def _scaffold_project(tmp_path: Path, project_name: str = "Test Device") -> Path:
    """Scaffold a minimal project from templates using the init workflow."""
    from medharness.workflows.init import _scaffold_dhf, _replace_placeholders
    _scaffold_dhf(tmp_path)
    _replace_placeholders(tmp_path, project_name)
    return tmp_path


class TestCheckUpgrade:
    def test_fresh_scaffold_all_up_to_date(self, tmp_path: Path) -> None:
        """Just-scaffolded project has no outdated files."""
        _scaffold_project(tmp_path)
        result = check_upgrade(tmp_path)
        assert result["outdated"] == []
        assert result["missing"] == []
        assert len(result["up_to_date"]) > 0

    def test_modified_file_reported_outdated(self, tmp_path: Path) -> None:
        """Modifying a scaffold file marks it outdated."""
        _scaffold_project(tmp_path)
        workflow_file = tmp_path / ".github" / "workflows" / "dhf.yml"
        workflow_file.write_text(workflow_file.read_text() + "\n# user modification\n")
        result = check_upgrade(tmp_path)
        outdated_files = [f["file"] for f in result["outdated"]]
        assert ".github/workflows/dhf.yml" in outdated_files

    def test_missing_file_reported(self, tmp_path: Path) -> None:
        """Deleting a scaffold file marks it as missing."""
        _scaffold_project(tmp_path)
        workflow_file = tmp_path / ".github" / "workflows" / "dhf.yml"
        workflow_file.unlink()
        result = check_upgrade(tmp_path)
        missing_files = [f["file"] for f in result["missing"]]
        assert ".github/workflows/dhf.yml" in missing_files

    def test_result_keys_present(self, tmp_path: Path) -> None:
        _scaffold_project(tmp_path)
        result = check_upgrade(tmp_path)
        assert set(result.keys()) >= {
            "installed_version", "files_checked", "up_to_date",
            "outdated", "missing", "summary",
        }

    def test_files_checked_count(self, tmp_path: Path) -> None:
        _scaffold_project(tmp_path)
        result = check_upgrade(tmp_path)
        total = len(result["up_to_date"]) + len(result["outdated"]) + len(result["missing"])
        assert result["files_checked"] == total


class TestApplyUpgrade:
    def test_apply_restores_modified_file(self, tmp_path: Path) -> None:
        _scaffold_project(tmp_path)
        workflow_file = tmp_path / ".github" / "workflows" / "dhf.yml"
        original = workflow_file.read_text()
        workflow_file.write_text(original + "\n# user modification\n")

        result = apply_upgrade(tmp_path)
        assert ".github/workflows/dhf.yml" in result.get("applied", [])
        assert workflow_file.read_text() == original

    def test_apply_creates_missing_file(self, tmp_path: Path) -> None:
        _scaffold_project(tmp_path)
        workflow_file = tmp_path / ".github" / "workflows" / "dhf.yml"
        workflow_file.unlink()

        result = apply_upgrade(tmp_path)
        assert ".github/workflows/dhf.yml" in result.get("applied", [])
        assert workflow_file.exists()

    def test_apply_result_has_applied_key(self, tmp_path: Path) -> None:
        _scaffold_project(tmp_path)
        result = apply_upgrade(tmp_path)
        assert "applied" in result

    def test_apply_noop_when_up_to_date(self, tmp_path: Path) -> None:
        _scaffold_project(tmp_path)
        result = apply_upgrade(tmp_path)
        assert result["applied"] == []


class TestUpgradeCLI:
    def test_up_to_date_exits_zero(self, tmp_path: Path) -> None:
        _scaffold_project(tmp_path)
        r = CliRunner().invoke(main, ["upgrade", "--project-dir", str(tmp_path)])
        assert r.exit_code == 0, r.output
        payload = json.loads(r.output.splitlines()[0])
        assert payload["outdated"] == []
        assert payload["missing"] == []

    def test_outdated_exits_nonzero_without_apply(self, tmp_path: Path) -> None:
        _scaffold_project(tmp_path)
        workflow_file = tmp_path / ".github" / "workflows" / "dhf.yml"
        workflow_file.write_text(workflow_file.read_text() + "\n# stale\n")
        r = CliRunner().invoke(main, ["upgrade", "--project-dir", str(tmp_path)])
        assert r.exit_code != 0
        assert "OUTDATED" in r.output

    def test_apply_flag_exits_zero(self, tmp_path: Path) -> None:
        _scaffold_project(tmp_path)
        workflow_file = tmp_path / ".github" / "workflows" / "dhf.yml"
        workflow_file.write_text(workflow_file.read_text() + "\n# stale\n")
        r = CliRunner().invoke(main, ["upgrade", "--apply", "--project-dir", str(tmp_path)])
        assert r.exit_code == 0, r.output
        assert "UPDATED" in r.output

    def test_output_json_shape(self, tmp_path: Path) -> None:
        _scaffold_project(tmp_path)
        r = CliRunner().invoke(main, ["upgrade", "--project-dir", str(tmp_path)])
        payload = json.loads(r.output.splitlines()[0])
        assert "installed_version" in payload
        assert "files_checked" in payload
        assert isinstance(payload["up_to_date"], list)
        assert isinstance(payload["outdated"], list)
        assert isinstance(payload["missing"], list)
