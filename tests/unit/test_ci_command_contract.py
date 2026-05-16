"""End-to-end contract tests for the CI generate-* CLI commands.

Drives the actual Click commands (with ``_run_claude`` and validators
patched so no LLM is invoked). Asserts that:

- stdout is parseable JSON.
- The JSON has the documented keys.
- The stderr summary contains the elements clients display.

This complements ``test_response_contract.py`` (which tests the service
function directly) by also exercising ``cli/ci.py`` ``_format_summary``
and the ``json.dumps``/``click.echo`` plumbing.

Covered stages: develop-cr, validate-code, validate-branch.
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


# Click's test runner mixes stderr into ``Result.output`` by default, so the
# CI summary assertions intentionally check ``r.output`` rather than ``r.stderr``.


class TestDevelopCrJsonContract:
    @pytest.fixture(autouse=True)
    def stub_session(self, monkeypatch):
        monkeypatch.setattr("medharness.services.cr_generation.get_session", lambda pr: "")
        monkeypatch.setattr("medharness.services.cr_generation.put_session", lambda pr, sid: None)

    def test_json_payload_has_documented_keys(self, dhf):
        runner = CliRunner()
        with patch("medharness.services.cr_generation._run_claude",
                   return_value=(0, "", "")), \
             patch("medharness.services.code_validation.validate_code",
                   return_value=[]), \
             patch("subprocess.run", return_value=_empty_diff()):
            r = runner.invoke(main, ["--dhf", str(dhf), "ci", "develop-cr", "--cr", "CR-200"])
        assert r.exit_code == 0, (r.output, r.stderr)
        payload = _split_stdout_json(r.stdout)
        for key in (
            "cr_id", "stage", "outcome", "summary", "timing", "inputs",
            "progress", "steps", "artifacts", "diagnostics", "warnings", "errors",
        ):
            assert key in payload, f"missing {key}"
        assert payload["stage"] == "develop"
        for legacy in ("items_created", "items_updated", "files_written", "status", "corrections", "validation"):
            assert legacy not in payload, f"removed key reappeared: {legacy}"


class TestValidateCodeJsonContract:
    def test_json_payload_has_documented_keys(self, dhf):
        runner = CliRunner()
        with patch("medharness.services.code_validation.validate_code", return_value=[]):
            r = runner.invoke(main, ["--dhf", str(dhf), "ci", "validate-code", "--cr", "CR-400"])
        assert r.exit_code == 0, (r.output, r.stderr)
        payload = _split_stdout_json(r.stdout)
        for key in ("cr_id", "stage", "passed", "since_ref", "errors"):
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
            "spec_path": None,
            "expected_dhf_changes": True,
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
            "dhf_item_changes", "code_changes", "errors",
        ):
            assert key in payload, f"missing {key}"
        assert payload["passed"] is True

    def test_errors_propagate_and_exit_non_zero(self, dhf):
        branch_result = {
            "cr_id": "CR-501",
            "since_ref": "origin/main",
            "passed": False,
            "spec_path": None,
            "expected_dhf_changes": True,
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


class TestAdvanceStageContract:
    """ci advance-stage: exits 0 on success, exits 1 when add_label fails."""

    def test_exits_zero_on_success(self):
        runner = CliRunner()
        with patch("medharness.services.github_pr.remove_label", return_value=True), \
             patch("medharness.services.github_pr.add_label", return_value=True):
            r = runner.invoke(main, [
                "ci", "advance-stage",
                "--pr", "7", "--from-stage", "cr", "--to-stage", "design",
            ])
        assert r.exit_code == 0, r.output
        payload = json.loads(r.stdout.splitlines()[0])
        assert payload["ok"] is True
        assert payload["from_label"] == "cr:stage/cr"
        assert payload["to_label"] == "cr:stage/design"

    def test_exits_one_when_add_label_fails(self):
        runner = CliRunner()
        with patch("medharness.services.github_pr.remove_label", return_value=True), \
             patch("medharness.services.github_pr.add_label", return_value=False):
            r = runner.invoke(main, [
                "ci", "advance-stage",
                "--pr", "7", "--from-stage", "cr", "--to-stage", "design",
            ])
        assert r.exit_code == 1, r.output
        payload = json.loads(r.stdout.splitlines()[0])
        assert payload["ok"] is False
        assert "FAIL" in r.output

    def test_custom_label_prefix(self):
        runner = CliRunner()
        with patch("medharness.services.github_pr.remove_label", return_value=True), \
             patch("medharness.services.github_pr.add_label", return_value=True):
            r = runner.invoke(main, [
                "ci", "advance-stage",
                "--pr", "3", "--from-stage", "design", "--to-stage", "code",
                "--label-prefix", "stage/",
            ])
        assert r.exit_code == 0, r.output
        payload = json.loads(r.stdout.splitlines()[0])
        assert payload["from_label"] == "stage/design"
        assert payload["to_label"] == "stage/code"

    def test_also_updates_issue_when_provided(self):
        calls: list[tuple] = []

        def _add(number, label, **kw):
            calls.append(("add", number, label))
            return True

        def _remove(number, label, **kw):
            calls.append(("remove", number, label))
            return True

        runner = CliRunner()
        with patch("medharness.services.github_pr.remove_label", side_effect=_remove), \
             patch("medharness.services.github_pr.add_label", side_effect=_add):
            r = runner.invoke(main, [
                "ci", "advance-stage",
                "--pr", "7", "--from-stage", "design", "--to-stage", "code",
                "--issue", "42",
            ])
        assert r.exit_code == 0, r.output
        added_numbers = [n for op, n, _ in calls if op == "add"]
        assert 7 in added_numbers
        assert 42 in added_numbers
