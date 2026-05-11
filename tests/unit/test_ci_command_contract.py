"""End-to-end contract tests for the CI generate-* CLI commands.

Drives the actual Click commands (with ``_run_claude`` and validators
patched so no LLM is invoked). Asserts that:

- stdout is parseable JSON.
- The JSON has the documented keys.
- The stderr summary contains the elements clients display.

This complements ``test_response_contract.py`` (which tests the service
function directly) by also exercising ``cli/ci.py`` ``_format_summary``
and the ``json.dumps``/``click.echo`` plumbing.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from medharness.cli import main


@pytest.fixture
def dhf(tmp_path: Path) -> Path:
    d = tmp_path / "DHF"
    d.mkdir()
    return d


def _empty_diff() -> MagicMock:
    return MagicMock(stdout="", returncode=0)


def _split_stdout_json(stdout: str) -> dict:
    """The CLI emits JSON on the first line and may follow with trace text.

    Take the first non-empty JSON-shaped line.
    """
    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            return json.loads(line)
    raise AssertionError(f"no JSON line in stdout:\n{stdout}")


class TestAnalyzeCrJsonContract:
    def test_json_payload_has_documented_keys(self, dhf):
        spec_path = dhf.parent / "docs" / "cr-specs" / "CR-001-Spec.md"
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        spec_path.write_text(
            '---\ncr_id: "CR-001"\ndirection_fit: "in-scope"\n'
            'affected_items: []\nproposed_new_items: []\n'
            'design_impact_summary: "Test summary."\n'
            'test_plan:\n  auto_covered: []\n'
            '  needs_new_tc: []\n  must_be_manual: []\n---\n',
            encoding="utf-8",
        )
        runner = CliRunner()
        with patch("medharness.services.cr_generation._run_claude",
                   return_value=(0, "")):
            r = runner.invoke(main, ["--dhf", str(dhf), "ci", "analyze-cr", "--cr", "CR-001"])
        assert r.exit_code == 0, (r.output, r.stderr)
        payload = _split_stdout_json(r.stdout)
        for key in (
            "cr_id", "stage", "status", "corrections", "validation", "errors",
            "started_at", "elapsed_ms", "spec_path", "analysis", "spec_json_path",
        ):
            assert key in payload, f"missing {key}; got {sorted(payload)}"
        assert payload["stage"] == "spec"

    def test_stderr_summary_format(self, dhf):
        spec_path = dhf.parent / "docs" / "cr-specs" / "CR-002-Spec.md"
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        spec_path.write_text(
            '---\ncr_id: "CR-002"\ndirection_fit: "in-scope"\n'
            'affected_items: []\nproposed_new_items: []\n'
            'design_impact_summary: "Test summary."\n'
            'test_plan:\n  auto_covered: []\n'
            '  needs_new_tc: []\n  must_be_manual: []\n---\n',
            encoding="utf-8",
        )
        runner = CliRunner()
        with patch("medharness.services.cr_generation._run_claude",
                   return_value=(0, "")):
            r = runner.invoke(main, ["--dhf", str(dhf), "ci", "analyze-cr", "--cr", "CR-002"])
        assert r.exit_code == 0
        assert "OK Spec generated for CR-002" in r.stderr
        assert "validation:" in r.stderr
        assert "correction(s)" in r.stderr


class TestDesignCrJsonContract:
    def test_json_payload_has_documented_keys(self, dhf):
        runner = CliRunner()
        with patch("medharness.services.cr_generation._run_claude",
                   return_value=(0, "")), \
             patch("medharness.services.design_validation.validate_design",
                   return_value=[]), \
             patch("subprocess.run", return_value=_empty_diff()):
            r = runner.invoke(main, ["--dhf", str(dhf), "ci", "design-cr", "--cr", "CR-100"])
        assert r.exit_code == 0, (r.output, r.stderr)
        payload = _split_stdout_json(r.stdout)
        for key in (
            "cr_id", "stage", "status", "corrections", "validation", "errors",
            "started_at", "elapsed_ms", "items_changed",
        ):
            assert key in payload, f"missing {key}"
        assert payload["stage"] == "design"
        # Removed legacy fields must not reappear.
        for legacy in ("items_created", "items_updated", "files_written"):
            assert legacy not in payload, f"removed key reappeared: {legacy}"

    def test_residual_errors_propagate_to_stderr(self, dhf):
        residual = [{"field": "schema", "issue": "x", "fix": "y"}]
        runner = CliRunner()
        with patch("medharness.services.cr_generation._run_claude",
                   return_value=(0, "")), \
             patch("medharness.services.design_validation.validate_design",
                   side_effect=[residual, residual]), \
             patch("subprocess.run", return_value=_empty_diff()):
            r = runner.invoke(main, ["--dhf", str(dhf), "ci", "design-cr", "--cr", "CR-101"])
        assert r.exit_code == 0
        payload = _split_stdout_json(r.stdout)
        assert payload["status"] == "completed_with_errors"
        assert payload["errors"] == residual
        assert "residual errors: 1" in r.stderr


class TestDevelopCrJsonContract:
    def test_json_payload_has_documented_keys(self, dhf):
        runner = CliRunner()
        with patch("medharness.services.cr_generation._run_claude",
                   return_value=(0, "")), \
             patch("medharness.services.code_validation.validate_code",
                   return_value=[]), \
             patch("subprocess.run", return_value=_empty_diff()):
            r = runner.invoke(main, ["--dhf", str(dhf), "ci", "develop-cr", "--cr", "CR-200"])
        assert r.exit_code == 0, (r.output, r.stderr)
        payload = _split_stdout_json(r.stdout)
        for key in (
            "cr_id", "stage", "status", "corrections", "validation", "errors",
            "started_at", "elapsed_ms", "files_changed",
        ):
            assert key in payload, f"missing {key}"
        assert payload["stage"] == "develop"
        for legacy in ("items_created", "items_updated", "files_written"):
            assert legacy not in payload, f"removed key reappeared: {legacy}"


class TestValidateDesignJsonContract:
    def test_json_payload_has_documented_keys(self, dhf):
        runner = CliRunner()
        with patch("medharness.services.design_validation.validate_design", return_value=[]):
            r = runner.invoke(main, ["--dhf", str(dhf), "ci", "validate-design", "--cr", "CR-300"])
        assert r.exit_code == 0, (r.output, r.stderr)
        payload = _split_stdout_json(r.stdout)
        for key in ("cr_id", "stage", "passed", "spec_path", "errors"):
            assert key in payload, f"missing {key}"
        assert payload["stage"] == "design"
        assert payload["passed"] is True

    def test_errors_propagate_and_exit_non_zero(self, dhf):
        residual = [{"field": "schema", "issue": "x", "fix": "y"}]
        runner = CliRunner()
        with patch("medharness.services.design_validation.validate_design", return_value=residual):
            r = runner.invoke(main, ["--dhf", str(dhf), "ci", "validate-design", "--cr", "CR-301"])
        assert r.exit_code == 1
        payload = _split_stdout_json(r.stdout)
        assert payload["passed"] is False
        assert payload["errors"] == residual


class TestValidateCodeJsonContract:
    def test_json_payload_has_documented_keys(self, dhf):
        runner = CliRunner()
        with patch("medharness.services.code_validation.validate_code", return_value=[]):
            r = runner.invoke(main, ["--dhf", str(dhf), "ci", "validate-code", "--cr", "CR-400"])
        assert r.exit_code == 0, (r.output, r.stderr)
        payload = _split_stdout_json(r.stdout)
        for key in ("cr_id", "stage", "passed", "spec_path", "since_ref", "errors"):
            assert key in payload, f"missing {key}"
        assert payload["stage"] == "develop"
        assert payload["passed"] is True
        assert payload["since_ref"] == "origin/main"

    def test_errors_propagate_and_exit_non_zero(self, dhf):
        residual = [{"field": "test_plan.needs_new_tc", "issue": "x", "fix": "y"}]
        runner = CliRunner()
        with patch("medharness.services.code_validation.validate_code", return_value=residual):
            r = runner.invoke(main, [
                "--dhf", str(dhf), "ci", "validate-code", "--cr", "CR-401", "--since-ref", "origin/feature-base",
            ])
        assert r.exit_code == 1
        payload = _split_stdout_json(r.stdout)
        assert payload["passed"] is False
        assert payload["since_ref"] == "origin/feature-base"
        assert payload["errors"] == residual


class TestValidateBranchJsonContract:
    def test_json_payload_has_documented_keys(self, dhf):
        runner = CliRunner()
        branch_result = {
            "cr_id": "CR-500",
            "since_ref": "origin/main",
            "passed": True,
            "spec_path": str(dhf.parent / "docs" / "cr-specs" / "CR-500-Spec.md"),
            "expected_dhf_changes": True,
            "spec_changes": {"created": [], "updated": ["docs/cr-specs/CR-500-Spec.md"], "deleted": []},
            "dhf_item_changes": {"created": ["SRS-010"], "updated": [], "deleted": []},
            "code_changes": {"created": ["apps/client/src/feature.ts"], "updated": [], "deleted": []},
            "errors": [],
        }
        with patch("medharness.services.git.validate_atomic_branch", return_value=branch_result):
            r = runner.invoke(main, ["--dhf", str(dhf), "ci", "validate-branch", "--cr", "CR-500"])
        assert r.exit_code == 0, (r.output, r.stderr)
        payload = _split_stdout_json(r.stdout)
        for key in (
            "cr_id", "since_ref", "passed", "spec_path", "expected_dhf_changes",
            "spec_changes", "dhf_item_changes", "code_changes", "errors",
        ):
            assert key in payload, f"missing {key}"
        assert payload["passed"] is True

    def test_errors_propagate_and_exit_non_zero(self, dhf):
        branch_result = {
            "cr_id": "CR-501",
            "since_ref": "origin/main",
            "passed": False,
            "spec_path": str(dhf.parent / "docs" / "cr-specs" / "CR-501-Spec.md"),
            "expected_dhf_changes": True,
            "spec_changes": {"created": [], "updated": [], "deleted": []},
            "dhf_item_changes": {"created": [], "updated": [], "deleted": []},
            "code_changes": {"created": [], "updated": [], "deleted": []},
            "errors": [{"field": "code_branch", "issue": "x", "fix": "y"}],
        }
        runner = CliRunner()
        with patch("medharness.services.git.validate_atomic_branch", return_value=branch_result):
            r = runner.invoke(main, ["--dhf", str(dhf), "ci", "validate-branch", "--cr", "CR-501"])
        assert r.exit_code == 1
        payload = _split_stdout_json(r.stdout)
        assert payload["passed"] is False
        assert payload["errors"] == [{"field": "code_branch", "issue": "x", "fix": "y"}]
