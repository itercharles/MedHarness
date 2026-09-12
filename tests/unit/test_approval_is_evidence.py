"""Approval must be evidence, not a label.

The gate used to pass when `cr:approved/design` was on the PR. Anyone with write
access can add or remove that, it names no author, carries no time, and is not
tied to a revision — so it recorded that someone clicked, not that anyone
reviewed. `verify completion` meanwhile required an APR record, so one workflow
held two unrelated definitions of "approved".

A review carries author, time and the commit it covers. The commit is what makes
it evidence: approval of work that has since changed is not approval of what
ships.
"""

from __future__ import annotations

import json
from unittest.mock import patch

from medharness.services.pr_approval import approval_evidence

HEAD = "a" * 40
OLDER = "b" * 40


def _gh_returning(reviews, head=HEAD, rc=0):
    """Stand in for the two gh calls: head SHA, then the reviews endpoint."""
    def fake(args, *, token=""):
        if "headRefOid" in " ".join(args):
            return 0, head
        return rc, json.dumps(reviews)
    return fake


def _review(state="APPROVED", commit=HEAD, login="reviewer"):
    return {"state": state, "commit_id": commit, "login": login,
            "submitted_at": "2026-09-12T00:00:00Z"}


class TestWhatCounts:
    def test_an_approving_review_of_the_head_commit_passes(self) -> None:
        with patch("medharness.services.pr_approval._gh", _gh_returning([_review()])):
            e = approval_evidence(7, "design")
        assert e["approved"] is True
        assert e["approvals"][0]["by"] == "reviewer"

    def test_no_review_does_not_pass(self) -> None:
        with patch("medharness.services.pr_approval._gh", _gh_returning([])):
            e = approval_evidence(7, "design")
        assert e["approved"] is False
        assert e["reason"] == "no approving review"

    def test_a_comment_only_review_does_not_pass(self) -> None:
        with patch("medharness.services.pr_approval._gh",
                   _gh_returning([_review(state="COMMENTED")])):
            assert approval_evidence(7, "design")["approved"] is False

    def test_changes_requested_does_not_pass(self) -> None:
        with patch("medharness.services.pr_approval._gh",
                   _gh_returning([_review(state="CHANGES_REQUESTED")])):
            assert approval_evidence(7, "design")["approved"] is False


class TestApprovalIsBoundToARevision:
    """The half a label cannot express."""

    def test_an_approval_of_an_earlier_commit_does_not_pass(self) -> None:
        with patch("medharness.services.pr_approval._gh",
                   _gh_returning([_review(commit=OLDER)])):
            e = approval_evidence(7, "design")
        assert e["approved"] is False
        assert e["reason"] == "every approving review is against an earlier commit"
        assert e["stale_approvals"][0]["commit"] == OLDER

    def test_a_fresh_approval_alongside_a_stale_one_passes(self) -> None:
        with patch("medharness.services.pr_approval._gh",
                   _gh_returning([_review(commit=OLDER, login="early"), _review(login="late")])):
            e = approval_evidence(7, "design")
        assert e["approved"] is True
        assert [a["by"] for a in e["approvals"]] == ["late"]
        assert [a["by"] for a in e["stale_approvals"]] == ["early"]

    def test_an_approval_with_no_commit_is_not_trusted(self) -> None:
        with patch("medharness.services.pr_approval._gh",
                   _gh_returning([_review(commit=None)])):
            assert approval_evidence(7, "design")["approved"] is False


class TestItFailsClosed:
    def test_unreadable_reviews_do_not_pass(self) -> None:
        with patch("medharness.services.pr_approval._gh", _gh_returning([], rc=1)):
            e = approval_evidence(7, "design")
        assert e["approved"] is False
        assert "could not be read" in e["reason"]

    def test_an_unknown_head_does_not_pass(self) -> None:
        with patch("medharness.services.pr_approval._gh", _gh_returning([_review()], head="")):
            assert approval_evidence(7, "design")["approved"] is False


def test_a_label_no_longer_decides() -> None:
    """The regression this replaces: labels are not consulted at all.

    Reads the call graph rather than the text — the docstring explains why a
    label is not evidence, and a word-search would trip on that.
    """
    import ast
    import inspect

    from medharness.services import pr_approval

    tree = ast.parse(inspect.getsource(pr_approval.approval_evidence))
    called = {
        n.func.id if isinstance(n.func, ast.Name) else getattr(n.func, "attr", "")
        for n in ast.walk(tree) if isinstance(n, ast.Call)
    }
    assert "label_for_stage" not in called, (
        "approval_evidence consults a label again; a label has no author, no "
        "time and no revision"
    )
    strings = " ".join(
        n.value for n in ast.walk(tree)
        if isinstance(n, ast.Constant) and isinstance(n.value, str)
    )
    assert "labels" not in strings, "a gh query still asks for labels"
