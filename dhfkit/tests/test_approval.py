"""Tests for approval records.

An approval says who accepted what, against which state of the design. Before
these records existed that account lived in a GitHub label and a markdown file —
outside the DHF, so absent from the traceability matrix, from evidence bundles,
and from every gate.

The property most of these tests defend is that the record cannot drift from
what actually happened: the approved revision is the commit, never a field.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

import dhfkit.api as api
from dhfkit.approval import (
    find_approvals,
    import_review_files,
    record_approval,
    resolve_approval,
)


@pytest.fixture
def dhf(tmp_path: Path) -> Path:
    """A DHF built from the bundled templates — dhfkit must not import medharness."""
    templates = Path(__file__).resolve().parents[1] / "templates"
    root = tmp_path / "DHF"
    for src, dst in (("config", "config"), ("items", "items")):
        source = templates / src
        if source.is_dir():
            shutil.copytree(source, root / dst, dirs_exist_ok=True)
    return root


def _git(dhf: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=T", *args],
        cwd=dhf.parent, check=True, capture_output=True,
    )


@pytest.fixture
def git_dhf(dhf: Path) -> Path:
    _git(dhf, "init", "-q")
    _git(dhf, "add", "-A")
    _git(dhf, "commit", "-qm", "initial DHF")
    return dhf


class TestRecording:
    def test_creates_an_apr_item(self, dhf: Path) -> None:
        item = record_approval(
            dhf, approves="CR-001", stage="design",
            verdict="approved", approver="qa@example.com",
        )
        assert item["id"].startswith("APR-")
        assert item["verdict"] == "approved"
        assert item["approves"] == ["CR-001"]

    def test_approver_is_required(self, dhf: Path) -> None:
        """A decision nobody is accountable for is not a record worth writing."""
        with pytest.raises(ValueError, match="approver is required"):
            record_approval(dhf, approves="CR-001", stage="design",
                            verdict="approved", approver="   ")

    @pytest.mark.parametrize("verdict", ["approved", "rejected", "needs_revision"])
    def test_every_modelled_verdict_is_accepted(self, dhf: Path, verdict: str) -> None:
        item = record_approval(dhf, approves="CR-001", stage="design",
                               verdict=verdict, approver="qa@example.com")
        assert item["verdict"] == verdict

    def test_unmodelled_verdict_is_rejected(self, dhf: Path) -> None:
        with pytest.raises(ValueError, match="verdict must be one of"):
            record_approval(dhf, approves="CR-001", stage="design",
                            verdict="looks-fine", approver="qa@example.com")

    def test_unmodelled_stage_is_rejected(self, dhf: Path) -> None:
        with pytest.raises(ValueError, match="stage must be one of"):
            record_approval(dhf, approves="CR-001", stage="lunch",
                            verdict="approved", approver="qa@example.com")

    def test_record_carries_no_revision_field(self, dhf: Path) -> None:
        """The revision is the commit; a field could be edited to disagree."""
        item = record_approval(dhf, approves="CR-001", stage="design",
                               verdict="approved", approver="qa@example.com")
        assert "reviewed_revision" not in item
        assert "approval_date" not in item


class TestQuery:
    def test_narrows_by_artifact_and_stage(self, dhf: Path) -> None:
        record_approval(dhf, approves="CR-001", stage="design",
                        verdict="approved", approver="a@x")
        record_approval(dhf, approves="CR-001", stage="develop",
                        verdict="approved", approver="a@x")
        record_approval(dhf, approves="CR-002", stage="design",
                        verdict="rejected", approver="a@x")

        assert len(find_approvals(dhf, approves="CR-001")) == 2
        assert len(find_approvals(dhf, approves="CR-001", stage="design")) == 1
        assert len(find_approvals(dhf)) == 3

    def test_empty_when_nothing_recorded(self, dhf: Path) -> None:
        assert find_approvals(dhf, approves="CR-001") == []


class TestRevisionResolution:
    def test_resolves_the_introducing_commit(self, git_dhf: Path) -> None:
        record_approval(git_dhf, approves="CR-001", stage="design",
                        verdict="approved", approver="qa@example.com")
        _git(git_dhf, "add", "-A")
        _git(git_dhf, "commit", "-qm", "APR: approve CR-001")

        result = resolve_approval(git_dhf, "APR-001")
        assert result["resolved"] is True
        assert len(result["revision"]) == 40, "audit trails need the full hash"
        assert result["short_revision"] == result["revision"][:8]
        assert result["date"]

    def test_uncommitted_record_is_reported_not_faked(self, git_dhf: Path) -> None:
        """A record created moments ago has no revision yet — say so."""
        record_approval(git_dhf, approves="CR-001", stage="design",
                        verdict="approved", approver="qa@example.com")

        result = resolve_approval(git_dhf, "APR-001")
        assert result["resolved"] is False
        assert result["revision"] is None
        assert "uncommitted" in result["reason"]

    def test_non_git_dhf_is_reported(self, dhf: Path) -> None:
        record_approval(dhf, approves="CR-001", stage="design",
                        verdict="approved", approver="qa@example.com")
        result = resolve_approval(dhf, "APR-001")
        assert result["resolved"] is False
        assert "git" in result["reason"]

    def test_later_edits_do_not_move_the_revision(self, git_dhf: Path) -> None:
        """The decision was made against the state at the introducing commit."""
        record_approval(git_dhf, approves="CR-001", stage="design",
                        verdict="approved", approver="qa@example.com")
        _git(git_dhf, "add", "-A")
        _git(git_dhf, "commit", "-qm", "APR: approve CR-001")
        first = resolve_approval(git_dhf, "APR-001")["revision"]

        api.update_item(git_dhf, "APR-001", {"notes": "typo fixed"}, author="t")
        _git(git_dhf, "add", "-A")
        _git(git_dhf, "commit", "-qm", "fix typo")

        assert resolve_approval(git_dhf, "APR-001")["revision"] == first

    def test_unknown_record_raises(self, dhf: Path) -> None:
        with pytest.raises(ValueError, match="not found"):
            resolve_approval(dhf, "APR-999")


class TestLegacyImport:
    def _review(self, dhf: Path, cr: str, verdict: str, kind: str = "Design") -> Path:
        reviews = dhf.parent / "docs" / "reviews"
        reviews.mkdir(parents=True, exist_ok=True)
        path = reviews / f"{cr}-{kind}-Review.md"
        path.write_text(f"# {cr} {kind} Review\n\n**Verdict:** {verdict}\n")
        return reviews

    def test_code_review_imports_as_the_develop_stage(self, dhf: Path) -> None:
        """A code review is a decision about develop, not design.

        Found by running the importer against ContourLab, whose only review file
        is CR-013-Code-Review.md — the original pattern matched design reviews
        only and would have skipped it silently.
        """
        reviews = self._review(dhf, "CR-013", "Needs Revision", kind="Code")

        result = import_review_files(dhf, reviews, approver="qa@example.com")

        assert result["imported"][0]["stage"] == "develop"
        assert find_approvals(dhf, approves="CR-013", stage="develop")
        assert find_approvals(dhf, approves="CR-013", stage="design") == []

    def test_both_kinds_coexist_for_one_cr(self, dhf: Path) -> None:
        self._review(dhf, "CR-001", "Approved", kind="Design")
        reviews = self._review(dhf, "CR-001", "Approved", kind="Code")

        result = import_review_files(dhf, reviews, approver="qa@example.com")

        stages = {e["stage"] for e in result["imported"]}
        assert stages == {"design", "develop"}

    def test_imports_each_verdict(self, dhf: Path) -> None:
        self._review(dhf, "CR-001", "Approved")
        self._review(dhf, "CR-002", "Needs Revision")
        reviews = self._review(dhf, "CR-003", "Rejected")

        result = import_review_files(dhf, reviews, approver="qa@example.com")

        verdicts = {e["verdict"] for e in result["imported"]}
        assert verdicts == {"approved", "needs_revision", "rejected"}
        assert result["errors"] == []

    def test_rerunning_skips_rather_than_duplicating(self, dhf: Path) -> None:
        reviews = self._review(dhf, "CR-001", "Approved")
        import_review_files(dhf, reviews, approver="qa@example.com")

        again = import_review_files(dhf, reviews, approver="qa@example.com")
        assert again["imported"] == []
        assert "already has a design record" in again["skipped"][0]["reason"]
        assert len(find_approvals(dhf, approves="CR-001")) == 1

    def test_file_without_a_verdict_is_skipped(self, dhf: Path) -> None:
        reviews = dhf.parent / "docs" / "reviews"
        reviews.mkdir(parents=True)
        (reviews / "CR-001-Design-Review.md").write_text("# Review\n\nStill drafting.\n")

        result = import_review_files(dhf, reviews, approver="qa@example.com")
        assert result["imported"] == []
        assert "Verdict" in result["skipped"][0]["reason"]

    def test_missing_directory_is_reported(self, dhf: Path) -> None:
        result = import_review_files(dhf, dhf.parent / "nowhere")
        assert result["imported"] == []
        assert result["errors"]

    def test_imported_record_notes_its_provenance(self, dhf: Path) -> None:
        reviews = self._review(dhf, "CR-001", "Approved")
        import_review_files(dhf, reviews, approver="qa@example.com")

        item = find_approvals(dhf, approves="CR-001")[0]
        assert "Backfilled" in item["notes"]
        assert "CR-001-Design-Review.md" in item["scope"]
