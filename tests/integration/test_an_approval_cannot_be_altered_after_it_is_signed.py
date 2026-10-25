"""An approval record is signed as a file and only ever added: tampering fails, and so does history rewritten."""

from __future__ import annotations

from pathlib import Path

import pytest
from fixtures.approvals import Project, build_project, git


@pytest.fixture
def project(tmp_path: Path) -> Project:
    project = build_project(tmp_path)
    project.ready_to_release()
    project.release()
    assert project.sign("Lead").exit_code == 0
    git(project.root, "add", "-A")
    git(project.root, "commit", "-qm", "signed")
    git(project.root, "checkout", "-q", "main")
    git(project.root, "merge", "-q", "--ff-only", "feat")
    git(project.root, "checkout", "-q", "-b", "next")
    return project


def _srs_is_unsigned(answer: dict) -> bool:
    return any("SRS document" in e for e in answer["errors"])


def test_a_signed_release_stands_once_merged(project: Project) -> None:
    assert not _srs_is_unsigned(project.verify("--release", "1.0.0"))


@pytest.mark.dhf_links("SRS-019")
@pytest.mark.dhf_testing("T1")
def test_a_tampered_approval_fails_its_signature_and_stops_counting(project: Project) -> None:
    file = project.records()[0]
    file.write_text(file.read_text().replace("id: SRS", "id: SYS"), encoding="utf-8")

    answer = project.verify("--release", "1.0.0")

    assert answer["passed"] is False
    assert any("signature does not verify" in e for e in answer["errors"])
    assert _srs_is_unsigned(answer)


@pytest.mark.dhf_links("SRS-019")
@pytest.mark.dhf_testing("T2")
def test_an_approval_without_its_signature_counts_for_nothing(project: Project) -> None:
    project.records()[0].with_suffix(".yaml.sig").unlink()

    answer = project.verify("--release", "1.0.0")

    assert any("no signature file" in e for e in answer["errors"])
    assert _srs_is_unsigned(answer)


@pytest.mark.dhf_links("SRS-019")
@pytest.mark.dhf_testing("T3")
def test_an_approval_that_names_another_signer_is_invalid(project: Project) -> None:
    project.forge("Lead", signer="Pat", roles=["software-lead"], documents=[project.pin("SRS")])

    assert any("its key belongs to Lead" in e for e in project.verify()["errors"])


@pytest.mark.dhf_links("SRS-020")
@pytest.mark.dhf_testing("T1")
def test_modifying_a_committed_approval_fails_append_only(project: Project) -> None:
    record = project.records()[0]
    record.write_text(record.read_text().replace("I have reviewed", "I skimmed"), encoding="utf-8")

    answer = project.verify()

    assert answer["passed"] is False
    assert any(f"{record.name} was modified" in e and "append-only" in e for e in answer["errors"])


@pytest.mark.dhf_links("SRS-020")
@pytest.mark.dhf_testing("T2")
def test_modifying_a_committed_signature_fails_append_only(project: Project) -> None:
    record = project.records()[0]
    sig = record.with_name(record.name + ".sig")
    sig.write_text(sig.read_text() + "\n", encoding="utf-8")

    assert any(f"{sig.name} was modified" in e for e in project.verify()["errors"])


@pytest.mark.dhf_links("SRS-020")
@pytest.mark.dhf_testing("T3")
def test_deleting_a_committed_approval_fails_append_only(project: Project) -> None:
    record = project.records()[0]
    record.unlink()

    answer = project.verify()

    assert answer["passed"] is False
    assert any(f"{record.name} was deleted" in e for e in answer["errors"])
