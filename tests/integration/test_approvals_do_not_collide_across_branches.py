"""Approvals given on parallel branches are separate files in the log, so merging them cannot collide."""

from __future__ import annotations

from pathlib import Path

from fixtures.approvals import build_project, git


def test_two_signers_on_two_branches_from_one_release_both_merge(tmp_path: Path) -> None:
    project = build_project(tmp_path)
    project.ready_to_release()
    project.release()
    git(project.root, "add", "-A")
    git(project.root, "commit", "-qm", "release pull request")
    git(project.root, "checkout", "-q", "main")
    git(project.root, "merge", "-q", "--ff-only", "feat")

    git(project.root, "checkout", "-q", "-b", "lead")
    assert project.sign("Lead").exit_code == 0
    git(project.root, "add", "-A")
    git(project.root, "commit", "-qm", "lead signs")
    git(project.root, "checkout", "-q", "main")
    git(project.root, "checkout", "-q", "-b", "pat")
    assert project.sign("Pat").exit_code == 0
    git(project.root, "add", "-A")
    git(project.root, "commit", "-qm", "pat signs")

    git(project.root, "merge", "-q", "--no-edit", "lead")

    assert len(project.records()) == 2
    answer = project.verify("--release", "1.0.0")
    errors = " ".join(answer["errors"])
    assert "SRS document" not in errors and "UC document" not in errors
    assert "SYS document" in errors and "The release of 1.0.0" in errors


def test_a_record_whose_id_differs_from_its_file_name_is_reported(tmp_path: Path) -> None:
    project = build_project(tmp_path)
    project.ready_to_release()
    project.release()
    project.forge("Lead", signer="Lead", roles=["software-lead"], documents=[project.pin("SRS")],
                  file_id="01JB3KQ7Z8X4M2N5P6R7S8T9VA")

    answer = project.verify("--release", "1.0.0")

    assert answer["passed"] is False
    assert any("differs from its file name" in e for e in answer["errors"])
    assert any("SRS document" in e for e in answer["errors"])
