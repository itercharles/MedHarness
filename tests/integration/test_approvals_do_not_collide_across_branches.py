"""Approvals given on parallel branches are separate files in the log, so merging them cannot collide."""

from __future__ import annotations

from pathlib import Path

from fixtures.approvals import build_project, git


def test_two_approvals_made_on_two_branches_from_one_base_both_merge(tmp_path: Path) -> None:
    project = build_project(tmp_path)
    project.edit("SRS-001", content="Changed on feat.")
    assert project.approve("Lead").exit_code == 0
    git(project.root, "add", "-A")
    git(project.root, "commit", "-qm", "feat approved")

    git(project.root, "checkout", "-q", "main")
    git(project.root, "checkout", "-q", "-b", "other")
    project.edit("SWDD-001", content="Changed on other.")
    assert project.approve("Lead").exit_code == 0
    git(project.root, "add", "-A")
    git(project.root, "commit", "-qm", "other approved")

    git(project.root, "merge", "-q", "--no-edit", "feat")

    assert len(project.records()) == 2
    answer = project.verify()
    assert answer["passed"] is True, answer["errors"]
    assert answer["summary"] == "2 item(s) checked; 0 missing approval(s)"


def test_an_approval_given_within_a_cr_is_filed_under_that_cr(tmp_path: Path) -> None:
    project = build_project(tmp_path)
    project.edit("CR-001", title="A changed CR.")

    assert project.approve("Lead", "--cr", "CR-001").exit_code == 0

    [record] = project.records()
    assert record.parent == project.dhf / "approvals" / "CR-001"
    assert project.verify()["passed"] is True


def test_a_record_whose_id_differs_from_its_file_name_is_reported(tmp_path: Path) -> None:
    project = build_project(tmp_path)
    project.edit("SRS-001", content="Changed.")
    project.forge("Lead", signer="Lead", roles=["software-lead"], items=[project.pin("SRS-001")],
                  file_id="01JB3KQ7Z8X4M2N5P6R7S8T9VA")

    answer = project.verify()

    assert answer["passed"] is False
    assert any("differs from its file name" in e for e in answer["errors"])
    assert any("SRS-001" in e and "no current approval" in e for e in answer["errors"])
