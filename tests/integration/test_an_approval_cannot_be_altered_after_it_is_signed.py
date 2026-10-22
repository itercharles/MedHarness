"""An APPROVAL item is signed as a file and only ever added: tampering fails, and so does history rewritten."""

from __future__ import annotations

from pathlib import Path

import pytest
from fixtures.approvals import Project, build_project, git


@pytest.fixture
def project(tmp_path: Path) -> Project:
    project = build_project(tmp_path)
    project.edit("SRS-001", content="Changed requirement.")
    assert project.approve("Lead").exit_code == 0
    assert project.verify()["passed"] is True
    git(project.root, "add", "-A")
    git(project.root, "commit", "-qm", "approved")
    git(project.root, "checkout", "-q", "main")
    git(project.root, "merge", "-q", "--ff-only", "feat")
    git(project.root, "checkout", "-q", "-b", "next")
    return project


def test_a_tampered_approval_fails_its_signature(project: Project) -> None:
    file = project.item_file("APR-001")
    file.write_text(file.read_text().replace("SRS-001", "SRS-002"), encoding="utf-8")

    answer = project.verify("--all")

    assert answer["passed"] is False
    assert any("signature does not verify" in e for e in answer["errors"])
    assert any("SRS-001" in e and "no current approval" in e for e in answer["errors"])


def test_an_approval_without_its_signature_counts_for_nothing(project: Project) -> None:
    project.item_file("APR-001").with_name("APR-001.yaml.sig").unlink()

    answer = project.verify()

    assert answer["passed"] is False
    assert any("no signature file" in e for e in answer["errors"])


def test_an_approval_that_names_another_signer_is_invalid(project: Project) -> None:
    project.forge("Lead", signer="Pat", roles=["software-lead"], items=[project.pin("SRS-001")])

    assert any("its key belongs to Lead" in e for e in project.verify()["errors"])


def test_modifying_a_committed_approval_fails_append_only(project: Project) -> None:
    file = project.item_file("APR-001")
    file.write_text(file.read_text().replace("I have reviewed", "I skimmed"), encoding="utf-8")

    answer = project.verify()

    assert answer["passed"] is False
    assert any("APR-001.yaml was modified" in e and "append-only" in e for e in answer["errors"])


def test_modifying_a_committed_signature_fails_append_only(project: Project) -> None:
    sig = project.item_file("APR-001").with_name("APR-001.yaml.sig")
    sig.write_text(sig.read_text() + "\n", encoding="utf-8")

    assert any("APR-001.yaml.sig was modified" in e for e in project.verify()["errors"])


def test_deleting_a_committed_approval_fails_append_only(project: Project) -> None:
    project.item_file("APR-001").unlink()

    answer = project.verify()

    assert answer["passed"] is False
    assert any("APR-001.yaml was deleted" in e for e in answer["errors"])
