"""`--pr` means the run belongs to that PR, in CI; without it, local files change.

With `--pr` the stage revises from the PR's reviews when there are any, and
commits and pushes what it did to the PR's branch. Without it nothing is
committed or pushed.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from medharness.services import cr_generation, git


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True,
                          text=True, check=True).stdout.strip()


@pytest.fixture
def clone(tmp_path: Path) -> Path:
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(remote)], check=True)
    work = tmp_path / "work"
    subprocess.run(["git", "clone", "-q", str(remote), str(work)], check=True,
                   capture_output=True)
    _git(work, "config", "user.email", "ci@example.com")
    _git(work, "config", "user.name", "ci")
    (work / "README.md").write_text("base\n")
    _git(work, "add", "-A")
    _git(work, "commit", "-qm", "base")
    _git(work, "push", "-q", "origin", "HEAD:main")
    _git(work, "checkout", "-q", "-b", "design/CR-001")
    _git(work, "push", "-q", "origin", "design/CR-001")
    return work


class TestCommitAndPush:
    def test_the_work_reaches_the_branch(self, clone: Path, tmp_path: Path) -> None:
        (clone / "new.txt").write_text("made by the run\n")

        assert git.commit_and_push(clone, "design(CR-001): build plan", "design/CR-001") is None

        remote = tmp_path / "remote.git"
        files = subprocess.run(["git", "-C", str(remote), "ls-tree", "--name-only", "design/CR-001"],
                               capture_output=True, text=True, check=True).stdout.split()
        assert "new.txt" in files

    def test_a_failure_is_reported_not_raised(self, clone: Path) -> None:
        _git(clone, "remote", "set-url", "origin", str(clone.parent / "nowhere.git"))
        (clone / "new.txt").write_text("x\n")
        assert git.commit_and_push(clone, "m", "design/CR-001")


class TestPushToThePr:
    def test_an_unreadable_pr_is_an_error(self, clone: Path) -> None:
        errors: list[dict] = []
        with patch("medharness.services.cr_generation.gh", return_value=(1, "no such PR")):
            cr_generation._push_to_pr(clone, 7, "m", errors)
        assert errors and errors[0]["field"] == "pr_push"
        assert "no such PR" in errors[0]["issue"]

    def test_it_pushes_to_the_prs_branch(self, clone: Path) -> None:
        (clone / "new.txt").write_text("x\n")
        errors: list[dict] = []
        with patch("medharness.services.cr_generation.gh", return_value=(0, "design/CR-001")):
            cr_generation._push_to_pr(clone, 7, "m", errors)
        assert errors == []
        assert _git(clone, "status", "--porcelain") == ""


class TestRevisionNeedsSomethingToRevise:
    def _feedback(self, comments: int, reviews: int) -> dict:
        return {"prompt_text": "[]", "warnings": [],
                "diagnostics": {"comments_count": comments, "reviews_count": reviews}}

    def test_a_new_pr_with_no_reviews_generates(self) -> None:
        with patch.object(cr_generation, "_get_pr_feedback", return_value=self._feedback(0, 0)):
            assert cr_generation._pr_feedback(7, [], {}, []) is None

    def test_a_reviewed_pr_revises(self) -> None:
        with patch.object(cr_generation, "_get_pr_feedback", return_value=self._feedback(0, 1)):
            assert cr_generation._pr_feedback(7, [], {}, []) is not None


def test_without_pr_nothing_is_pushed(tmp_path: Path) -> None:
    from dhfkit.tests.fixtures import bare_dhf

    dhf = bare_dhf(tmp_path / "DHF")
    with patch.object(cr_generation, "_run_claude", return_value=(0, "", "")), \
         patch.object(cr_generation, "_push_to_pr") as push:
        cr_generation.generate_code("CR-001", dhf)
    push.assert_not_called()
