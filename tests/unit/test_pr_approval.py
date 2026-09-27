"""Tests for medharness.services.pr_approval."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from medharness.cli import main
from medharness.services.pr_approval import approval_evidence


# ── gh-dependent functions — graceful failure without gh CLI ─────────────────

class TestWithoutGh:
    def test_evidence_graceful_no_gh_cli(self, monkeypatch):
        """No gh means the reviews cannot be read, which is not an approval."""
        monkeypatch.setenv("PATH", "/nonexistent")
        monkeypatch.setenv("GH_TOKEN", "")
        monkeypatch.setenv("GITHUB_TOKEN", "")
        evidence = approval_evidence(42)
        assert evidence["approved"] is False
        assert "could not be read" in evidence["reason"]

# ── gh mock tests ─────────────────────────────────────────────────────────────

class TestWithMockedGh:
    def _mock_run(self, returncode: int, stdout: str) -> MagicMock:
        m = MagicMock()
        m.returncode = returncode
        m.stdout = stdout
        return m

    def test_an_approval_of_the_head_commit_counts(self):
        """Two gh calls: the head commit, then the reviews on it."""
        import json as _json

        head = "a" * 40
        reviews = _json.dumps([{"state": "APPROVED", "commit_id": head,
                                "login": "r", "submitted_at": "t"}])
        with patch("medharness.services.pr_approval.gh",
                   side_effect=[(0, head), (0, reviews)]):
            assert approval_evidence(42, token="tok")["approved"] is True

    def test_no_approving_review_is_not_an_approval(self):
        with patch("subprocess.run", return_value=self._mock_run(0, "false")):
            assert approval_evidence(42, token="tok")["approved"] is False

    def test_a_gh_error_is_not_an_approval(self):
        with patch("subprocess.run", return_value=self._mock_run(1, "")):
            assert approval_evidence(42, token="tok")["approved"] is False

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
            r = CliRunner().invoke(main, ["workflow", "check-approval", "--cr", "CR-001",
                                          "--pr", "42"])
        assert r.exit_code == 0, r.output
        payload = _first_json_line(r.output)
        assert payload["passed"] is True
        assert "reviewer" in payload["summary"], (
            f"the approver is not in what the caller receives: {payload['summary']}"
        )
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
            r = CliRunner().invoke(main, ["workflow", "check-approval", "--cr", "CR-001",
                                          "--pr", "42"])
        assert r.exit_code == 1
        assert "earlier commit" in r.output
        assert "bbbbbbb" in r.output, "the reviewed commit is not named"

    def test_the_payload_no_longer_carries_a_label(self):
        with patch("medharness.services.pr_approval.approval_evidence",
                   return_value=self.EVIDENCE):
            r = CliRunner().invoke(main, ["workflow", "check-approval", "--cr", "CR-001",
                                          "--pr", "42"])
        assert "label" not in json.dumps(_first_json_line(r.output))




