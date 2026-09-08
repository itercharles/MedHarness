"""An ID must mean one item for the life of the project.

The next-ID calculation looked only at items present on disk, so deleting
SRS-003 and creating another produced SRS-003 again — while git still held the
original. Every reference to it retargets silently: a CR's `affected_items`, an
approval record's `approves`, a test's `dhf_links`, a review comment.

For IEC 62304 traceability an identifier that means two things over a project's
life is a broken record, not a tidy one.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import dhfkit.api as api
from medharness.workflows.init import _replace_placeholders, _scaffold_dhf


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, capture_output=True, check=False)


def _commit(root: Path, message: str) -> None:
    _git(root, "add", "-A")
    _git(root, "-c", "user.email=t@e", "-c", "user.name=t", "commit", "-qm", message)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _scaffold_dhf(tmp_path)
    _replace_placeholders(tmp_path, "Reuse")
    _git(tmp_path, "init", "-q")
    _commit(tmp_path, "scaffold")
    return tmp_path


def _new_srs(dhf: Path, title: str) -> str:
    return api.create_item(
        dhf, {"type": "SRS", "title": title, "derives_from": ["SYS-001"]}, author="t"
    )["id"]


class TestADeletedIdIsRetired:
    def test_the_next_item_does_not_take_it(self, repo: Path) -> None:
        dhf = repo / "DHF"
        first = _new_srs(dhf, "first")
        _commit(repo, "add")

        api.delete_item(dhf, first)
        _commit(repo, "delete")

        second = _new_srs(dhf, "second")
        assert second != first, (
            f"{first} was deleted and handed to a different requirement. Every "
            f"reference to it now points at the wrong item."
        )

    def test_it_stays_retired_across_several_deletions(self, repo: Path) -> None:
        dhf = repo / "DHF"
        created = [_new_srs(dhf, f"r{i}") for i in range(3)]
        _commit(repo, "add three")
        for uid in created:
            api.delete_item(dhf, uid)
        _commit(repo, "delete three")

        again = [_new_srs(dhf, f"s{i}") for i in range(3)]
        assert not (set(again) & set(created)), f"reused: {sorted(set(again) & set(created))}"

    def test_ids_are_still_sequential_without_deletions(self, repo: Path) -> None:
        """The common path must not get holes."""
        dhf = repo / "DHF"
        ids = [_new_srs(dhf, f"r{i}") for i in range(3)]
        numbers = [int(i.rsplit("-", 1)[1]) for i in ids]
        assert numbers == list(range(numbers[0], numbers[0] + 3)), ids


class TestOutsideGit:
    def test_a_dhf_with_no_repository_still_creates_items(self, tmp_path: Path) -> None:
        """History is unavailable there; behave as before rather than fail."""
        _scaffold_dhf(tmp_path)
        _replace_placeholders(tmp_path, "NoGit")
        dhf = tmp_path / "DHF"
        assert _new_srs(dhf, "a").startswith("SRS-")
        assert _new_srs(dhf, "b").startswith("SRS-")
