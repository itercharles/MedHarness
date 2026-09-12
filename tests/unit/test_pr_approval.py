"""Tests for medharness.services.pr_approval."""

from __future__ import annotations

import json
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
    @pytest.mark.parametrize("body", [
        "/approve",
        "  /approve  ",
        "LGTM, looks good.\n\n/approve\n\nThanks.",
        "/APPROVE",
        "/Approve",
    ])
    def test_approve_variants(self, body):
        cmd = parse_approval_command(body)
        assert cmd is not None
        assert cmd.action == "approve"

    @pytest.mark.parametrize("body,expected_reason", [
        ("/reject needs more detail on risk items", "needs more detail on risk items"),
        ("/reject", ""),
        ("The direction_fit is wrong.\n\n/reject direction_fit should be out-of-scope", "direction_fit should be out-of-scope"),
        ("/REJECT too vague", "too vague"),
    ])
    def test_reject_variants(self, body, expected_reason):
        cmd = parse_approval_command(body)
        assert cmd is not None
        assert cmd.action == "reject"
        assert cmd.reason == expected_reason

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
        """Two gh calls now: the head commit, then the reviews on it."""
        import json as _json

        head = "a" * 40
        reviews = _json.dumps([{"state": "APPROVED", "commit_id": head,
                                "login": "r", "submitted_at": "t"}])
        with patch("medharness.services.pr_approval._gh",
                   side_effect=[(0, head), (0, reviews)]):
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



def _first_json_line(output: str) -> dict:
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            return json.loads(line)
    raise AssertionError(f"no JSON line in output:\n{output}")


class TestCiApproveGate:
    """The CLI reports the evidence, not just a verdict."""

    EVIDENCE = {
        "approved": True, "reason": "", "head_sha": "a" * 40,
        "approvals": [{"by": "reviewer", "at": "2026-09-12T00:00:00Z", "commit": "a" * 40}],
        "stale_approvals": [],
    }

    def test_an_approved_stage_passes_and_names_the_reviewer(self):
        with patch("medharness.services.pr_approval.approval_evidence",
                   return_value=self.EVIDENCE):
            r = CliRunner().invoke(main, ["approval", "check", "--cr", "CR-001",
                                          "--stage", "design", "--pr", "42"])
        assert r.exit_code == 0, r.output
        payload = _first_json_line(r.output)
        assert payload["approved"] is True
        assert payload["approvals"][0]["by"] == "reviewer"
        assert "reviewer" in r.output

    def test_a_stale_approval_fails_and_says_which_commit(self):
        evidence = {
            "approved": False,
            "reason": "every approving review is against an earlier commit",
            "head_sha": "a" * 40,
            "approvals": [],
            "stale_approvals": [{"by": "early", "at": "x", "commit": "b" * 40}],
        }
        with patch("medharness.services.pr_approval.approval_evidence",
                   return_value=evidence):
            r = CliRunner().invoke(main, ["approval", "check", "--cr", "CR-001",
                                          "--stage", "design", "--pr", "42"])
        assert r.exit_code == 1
        assert "earlier commit" in r.output
        assert "bbbbbbb" in r.output, "the reviewed commit is not named"

    def test_the_payload_no_longer_carries_a_label(self):
        with patch("medharness.services.pr_approval.approval_evidence",
                   return_value=self.EVIDENCE):
            r = CliRunner().invoke(main, ["approval", "check", "--cr", "CR-001",
                                          "--stage", "design", "--pr", "42"])
        assert "label" not in _first_json_line(r.output)




