"""`approval check` and `verify completion` must not disagree.

Before 0.24.0 the stage gate read a GitHub label while the closure gate required
an APR record — one workflow, two unrelated definitions of approved, and the
weaker one decided whether a stage could advance. 0.24.0 fixed the stage gate.
This closes the other half: given a pull request, closure reads the same review.

An APR item remains the record for an approval that never had a PR.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from medharness.services.ci import _check_design_review

APPROVED = {"approved": True, "reason": "", "head_sha": "a" * 40,
            "approvals": [{"by": "r", "at": "t", "commit": "a" * 40}],
            "stale_approvals": []}
STALE = {"approved": False,
         "reason": "every approving review is against an earlier commit",
         "head_sha": "a" * 40, "approvals": [],
         "stale_approvals": [{"by": "r", "at": "t", "commit": "b" * 40}]}


class TestClosureReadsTheReviewWhenGivenAPR:
    def test_an_approving_review_satisfies_closure(self, tmp_path: Path) -> None:
        with patch("medharness.services.pr_approval.approval_evidence", return_value=APPROVED):
            assert _check_design_review(tmp_path, "CR-001", pr_number=42) == []

    def test_a_stale_review_fails_closure(self, tmp_path: Path) -> None:
        with patch("medharness.services.pr_approval.approval_evidence", return_value=STALE):
            issues = _check_design_review(tmp_path, "CR-001", pr_number=42)
        assert issues and "earlier commit" in issues[0]["issue"]

    def test_the_dhf_is_not_consulted_when_a_pr_is_given(self, tmp_path: Path) -> None:
        """No APR item, no review file, and it still passes on the review alone."""
        with patch("medharness.services.pr_approval.approval_evidence", return_value=APPROVED), \
             patch("dhfkit.approval.find_approvals",
                   side_effect=AssertionError("closure fell back to the DHF")):
            assert _check_design_review(tmp_path, "CR-001", pr_number=42) == []


class TestWithoutAPRItFallsBackToTheRecord:
    def test_an_apr_item_still_works(self, tmp_path: Path) -> None:
        with patch("dhfkit.approval.find_approvals",
                   return_value=[{"id": "APR-001", "verdict": "approved"}]):
            assert _check_design_review(tmp_path, "CR-001") == []

    def test_no_record_at_all_fails(self, tmp_path: Path) -> None:
        with patch("dhfkit.approval.find_approvals", return_value=[]):
            assert _check_design_review(tmp_path, "CR-001") != []


def test_both_gates_call_the_same_function() -> None:
    """The guarantee, read from the call graph rather than trusted."""
    import ast
    import inspect

    from medharness.services import ci

    source = inspect.getsource(ci._check_design_review)
    called = {
        getattr(n.func, "id", "") or getattr(n.func, "attr", "")
        for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Call)
    }
    assert "approval_evidence" in called, (
        "closure no longer uses the evidence `approval check` uses; the two "
        "gates can disagree about whether a stage was approved"
    )
