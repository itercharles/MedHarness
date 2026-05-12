"""Tests for medharness.services.pr_approval."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from medharness.cli import main
from medharness.services.pr_approval import (
    ApprovalCommand,
    add_approval_label,
    check_approved,
    close_pr,
    label_for_stage,
    parse_approval_command,
    post_comment,
    stage_for_branch,
)


# ── parse_approval_command ────────────────────────────────────────────────────

class TestParseApprovalCommand:
    def test_approve_simple(self):
        cmd = parse_approval_command("/approve")
        assert cmd is not None
        assert cmd.action == "approve"

    def test_approve_with_leading_whitespace(self):
        cmd = parse_approval_command("  /approve  ")
        assert cmd is not None
        assert cmd.action == "approve"

    def test_approve_in_multiline_comment(self):
        body = "LGTM, looks good.\n\n/approve\n\nThanks."
        cmd = parse_approval_command(body)
        assert cmd is not None
        assert cmd.action == "approve"

    def test_approve_case_insensitive(self):
        assert parse_approval_command("/APPROVE") is not None
        assert parse_approval_command("/Approve") is not None

    def test_reject_with_reason(self):
        cmd = parse_approval_command("/reject needs more detail on risk items")
        assert cmd is not None
        assert cmd.action == "reject"
        assert cmd.reason == "needs more detail on risk items"

    def test_reject_without_reason(self):
        cmd = parse_approval_command("/reject")
        assert cmd is not None
        assert cmd.action == "reject"
        assert cmd.reason == ""

    def test_reject_in_multiline_comment(self):
        body = "The direction_fit is wrong.\n\n/reject direction_fit should be out-of-scope"
        cmd = parse_approval_command(body)
        assert cmd is not None
        assert cmd.action == "reject"
        assert cmd.reason == "direction_fit should be out-of-scope"

    def test_reject_case_insensitive(self):
        cmd = parse_approval_command("/REJECT too vague")
        assert cmd is not None
        assert cmd.action == "reject"

    def test_no_command_returns_none(self):
        assert parse_approval_command("LGTM!") is None
        assert parse_approval_command("") is None
        assert parse_approval_command("approved by reviewer") is None

    def test_approve_takes_priority_over_reject(self):
        body = "/approve\n/reject should not reach this"
        cmd = parse_approval_command(body)
        assert cmd is not None
        assert cmd.action == "approve"

    def test_approve_not_triggered_mid_word(self):
        # "/approver" should not match
        assert parse_approval_command("/approver") is None

    def test_reject_not_triggered_mid_word(self):
        # "/rejection" should not match
        assert parse_approval_command("/rejection") is None


# ── label_for_stage ──────────────────────────────────────────────────────────

class TestLabelForStage:
    def test_spec_label(self):
        assert label_for_stage("spec") == "cr-spec-approved"

    def test_design_label(self):
        assert label_for_stage("design") == "cr-design-approved"

    def test_develop_label(self):
        assert label_for_stage("develop") == "cr-code-approved"

    def test_unknown_stage_returns_none(self):
        assert label_for_stage("unknown") is None
        assert label_for_stage("") is None


# ── stage_for_branch ─────────────────────────────────────────────────────────

class TestStageForBranch:
    def test_spec_branch(self):
        assert stage_for_branch("spec/CR-001") == "spec"

    def test_design_branch(self):
        assert stage_for_branch("design/CR-034") == "design"

    def test_feat_branch(self):
        assert stage_for_branch("feat/CR-100") == "develop"

    def test_unknown_prefix(self):
        assert stage_for_branch("main") is None
        assert stage_for_branch("hotfix/CR-001") is None


# ── ApprovalCommand dataclass ─────────────────────────────────────────────────

class TestApprovalCommandDataclass:
    def test_frozen(self):
        cmd = ApprovalCommand(action="approve")
        with pytest.raises(Exception):
            cmd.action = "reject"  # type: ignore[misc]

    def test_default_reason(self):
        cmd = ApprovalCommand(action="reject")
        assert cmd.reason == ""


# ── gh-dependent functions — graceful failure without gh CLI ─────────────────

class TestGhDependentFunctions:
    def test_add_label_graceful_no_gh_cli(self, monkeypatch):
        monkeypatch.setenv("PATH", "/nonexistent")
        monkeypatch.setenv("GH_TOKEN", "")
        monkeypatch.setenv("GITHUB_TOKEN", "")
        assert add_approval_label(42, "spec") is False

    def test_post_comment_graceful_no_gh_cli(self, monkeypatch):
        monkeypatch.setenv("PATH", "/nonexistent")
        monkeypatch.setenv("GH_TOKEN", "")
        monkeypatch.setenv("GITHUB_TOKEN", "")
        assert post_comment(42, "hello") is False

    def test_close_pr_graceful_no_gh_cli(self, monkeypatch):
        monkeypatch.setenv("PATH", "/nonexistent")
        monkeypatch.setenv("GH_TOKEN", "")
        monkeypatch.setenv("GITHUB_TOKEN", "")
        assert close_pr(42) is False

    def test_check_approved_graceful_no_gh_cli(self, monkeypatch):
        monkeypatch.setenv("PATH", "/nonexistent")
        monkeypatch.setenv("GH_TOKEN", "")
        monkeypatch.setenv("GITHUB_TOKEN", "")
        assert check_approved(42, "spec") is False

    def test_add_label_unknown_stage(self, monkeypatch):
        monkeypatch.setenv("PATH", "/nonexistent")
        assert add_approval_label(42, "nonexistent") is False

    def test_check_approved_unknown_stage(self, monkeypatch):
        monkeypatch.setenv("PATH", "/nonexistent")
        assert check_approved(42, "nonexistent") is False


# ── gh mock tests ─────────────────────────────────────────────────────────────

class TestWithMockedGh:
    def _mock_run(self, returncode: int, stdout: str) -> MagicMock:
        m = MagicMock()
        m.returncode = returncode
        m.stdout = stdout
        return m

    def test_add_label_success(self):
        with patch("subprocess.run", return_value=self._mock_run(0, "")) as mock:
            result = add_approval_label(42, "spec", token="tok")
        assert result is True
        cmd = mock.call_args[0][0]
        assert "gh" in cmd[0]
        assert "--add-label" in cmd
        assert "cr-spec-approved" in cmd

    def test_add_label_failure(self):
        with patch("subprocess.run", return_value=self._mock_run(1, "")):
            assert add_approval_label(42, "spec", token="tok") is False

    def test_check_approved_true(self):
        with patch("subprocess.run", return_value=self._mock_run(0, "true")):
            assert check_approved(42, "design", token="tok") is True

    def test_check_approved_false_label_absent(self):
        with patch("subprocess.run", return_value=self._mock_run(0, "false")):
            assert check_approved(42, "design", token="tok") is False

    def test_check_approved_false_gh_error(self):
        with patch("subprocess.run", return_value=self._mock_run(1, "")):
            assert check_approved(42, "develop", token="tok") is False

    def test_post_comment_success(self):
        with patch("subprocess.run", return_value=self._mock_run(0, "https://gh/comment/1")):
            assert post_comment(42, "hello", token="tok") is True

    def test_close_pr_success(self):
        with patch("subprocess.run", return_value=self._mock_run(0, "")):
            assert close_pr(42, token="tok") is True


# ── CLI commands ──────────────────────────────────────────────────────────────

class TestCiParseApproval:
    def test_approve_command(self):
        runner = CliRunner()
        r = runner.invoke(main, ["ci", "parse-approval", "--comment", "/approve"])
        assert r.exit_code == 0, r.output
        import json
        payload = json.loads(r.output)
        assert payload["action"] == "approve"
        assert payload["reason"] == ""

    def test_reject_command(self):
        runner = CliRunner()
        r = runner.invoke(main, ["ci", "parse-approval", "--comment", "/reject needs revision"])
        assert r.exit_code == 0, r.output
        import json
        payload = json.loads(r.output)
        assert payload["action"] == "reject"
        assert payload["reason"] == "needs revision"

    def test_no_command(self):
        runner = CliRunner()
        r = runner.invoke(main, ["ci", "parse-approval", "--comment", "LGTM!"])
        assert r.exit_code == 0, r.output
        import json
        payload = json.loads(r.output)
        assert payload["action"] is None


def _first_json_line(output: str) -> dict:
    import json
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            return json.loads(line)
    raise AssertionError(f"no JSON line in output:\n{output}")


class TestCiApproveGate:
    def test_approved_exits_zero(self):
        runner = CliRunner()
        with patch("medharness.services.pr_approval.check_approved", return_value=True):
            r = runner.invoke(main, ["ci", "approve-gate", "--cr", "CR-001", "--stage", "spec", "--pr", "42"])
        assert r.exit_code == 0, r.output
        payload = _first_json_line(r.output)
        assert payload["approved"] is True
        assert payload["label"] == "cr-spec-approved"
        assert payload["cr_id"] == "CR-001"

    def test_not_approved_exits_one(self):
        runner = CliRunner()
        with patch("medharness.services.pr_approval.check_approved", return_value=False):
            r = runner.invoke(main, ["ci", "approve-gate", "--cr", "CR-001", "--stage", "spec", "--pr", "42"])
        assert r.exit_code == 1, r.output
        payload = _first_json_line(r.output)
        assert payload["approved"] is False

    def test_design_stage_label(self):
        runner = CliRunner()
        with patch("medharness.services.pr_approval.check_approved", return_value=True):
            r = runner.invoke(main, ["ci", "approve-gate", "--cr", "CR-042", "--stage", "design", "--pr", "7"])
        assert r.exit_code == 0, r.output
        payload = _first_json_line(r.output)
        assert payload["label"] == "cr-design-approved"

    def test_develop_stage_label(self):
        runner = CliRunner()
        with patch("medharness.services.pr_approval.check_approved", return_value=True):
            r = runner.invoke(main, ["ci", "approve-gate", "--cr", "CR-099", "--stage", "develop", "--pr", "10"])
        assert r.exit_code == 0, r.output
        payload = _first_json_line(r.output)
        assert payload["label"] == "cr-code-approved"

    def test_pass_message_in_output(self):
        runner = CliRunner()
        with patch("medharness.services.pr_approval.check_approved", return_value=True):
            r = runner.invoke(main, ["ci", "approve-gate", "--cr", "CR-001", "--stage", "spec", "--pr", "42"])
        assert "PASS" in r.output
        assert "cr-spec-approved" in r.output

    def test_fail_message_in_output(self):
        runner = CliRunner()
        with patch("medharness.services.pr_approval.check_approved", return_value=False):
            r = runner.invoke(main, ["ci", "approve-gate", "--cr", "CR-001", "--stage", "spec", "--pr", "42"])
        assert "FAIL" in r.output
        assert "cr-spec-approved" in r.output


class TestCiCrStatus:
    def test_explicit_stage_and_pr_reports_approved(self):
        runner = CliRunner()
        with patch("medharness.services.pr_approval.check_approved", return_value=True):
            r = runner.invoke(main, ["ci", "cr-status", "--cr", "CR-001", "--stage", "spec", "--pr", "42"])
        assert r.exit_code == 0, r.output
        payload = _first_json_line(r.output)
        assert payload["stage"] == "spec"
        assert payload["approval_label"] == "cr-spec-approved"
        assert payload["approval_state"] == "approved"
        assert payload["approved"] is True

    def test_explicit_stage_and_pr_reports_pending(self):
        runner = CliRunner()
        with patch("medharness.services.pr_approval.check_approved", return_value=False):
            r = runner.invoke(main, ["ci", "cr-status", "--cr", "CR-001", "--stage", "spec", "--pr", "42"])
        assert r.exit_code == 0, r.output
        payload = _first_json_line(r.output)
        assert payload["approval_state"] == "pending"
        assert payload["approved"] is False

    def test_branch_ref_infers_stage(self):
        runner = CliRunner()
        with patch("medharness.services.pr_approval.check_approved", return_value=True):
            r = runner.invoke(main, ["ci", "cr-status", "--cr", "CR-100", "--branch", "feat/CR-100", "--pr", "10"])
        assert r.exit_code == 0, r.output
        payload = _first_json_line(r.output)
        assert payload["stage"] == "develop"
        assert payload["approval_label"] == "cr-code-approved"

    def test_without_pr_reports_not_applicable(self):
        runner = CliRunner()
        r = runner.invoke(main, ["ci", "cr-status", "--cr", "CR-042", "--stage", "design"])
        assert r.exit_code == 0, r.output
        payload = _first_json_line(r.output)
        assert payload["approval_state"] == "not_applicable"
        assert payload["approved"] is None

    def test_unknown_branch_leaves_stage_blank(self):
        runner = CliRunner()
        r = runner.invoke(main, ["ci", "cr-status", "--cr", "CR-055", "--branch", "hotfix/CR-055"])
        assert r.exit_code == 0, r.output
        payload = _first_json_line(r.output)
        assert payload["stage"] == ""
        assert payload["approval_label"] is None
        assert payload["approval_state"] == "not_applicable"
