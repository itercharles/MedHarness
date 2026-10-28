"""`build approvals` writes the release's approval sheet once `verify approval --release` passes, and nothing before.

A specification states where its approval is shown whenever the project keeps an approvers list.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from fixtures.approvals import build_project
from medharness.validation.signing import Project

from medharness.results import ApprovalSheetReport
from medharness.services.approval import fingerprint

def _pdf_libraries_load() -> bool:
    try:
        from dhfkit.document_generation import load_weasyprint

        load_weasyprint()
    except (ImportError, OSError):
        return False
    return True


REQUIRED = os.environ.get("MEDHARNESS_REQUIRE_PDF") == "1"
LINE = "Approval: see the approval sheet of release 1.0.0."


@pytest.fixture
def project(tmp_path: Path) -> Project:
    project = build_project(tmp_path)
    project.ready_to_release()
    project.release()
    return project


def _sheet(project: Project, *extra: str):
    result = project.run("build", "approvals", "--release", "1.0.0", "--out-dir", str(project.root / "sheet"),
                         "--since-ref", "main", *extra)
    return result, ApprovalSheetReport.model_validate_json(result.stdout.splitlines()[0])


def _sign_all(project: Project) -> dict[str, str]:
    return {who: json.loads(project.sign(who).stdout)["id"] for who in ("Lead", "Pat", "Sam", "Quinn")}


def _fingerprint(project: Project, who: str) -> str:
    return fingerprint(project.keys[who].with_name(project.keys[who].name + ".pub").read_text())


@pytest.mark.dhf_links("SRS-066")
@pytest.mark.dhf_testing("T1")
def test_nothing_is_written_while_a_signature_is_missing(project: Project) -> None:
    project.sign("Lead")

    result, report = _sheet(project)

    assert result.exit_code == 1
    assert report.outcome == "completed_with_errors" and report.path is None
    assert any("SYS document" in e and "system-architect: Sam" in e for e in report.errors)
    assert not (project.root / "sheet").exists()


@pytest.mark.dhf_links("SRS-067")
@pytest.mark.dhf_testing("T1")
def test_a_signed_release_gets_a_sheet_naming_every_signer_record_and_key(project: Project) -> None:
    records = _sign_all(project)

    result, report = _sheet(project)

    assert result.exit_code == 0, result.stderr
    sheet = project.root / "sheet" / "approval-sheet.html"
    assert report.path == str(sheet) and report.outcome == "completed" and report.errors == []
    assert report.documents == 12 and report.signatures == 4
    html = sheet.read_text()
    manifest = project.manifest()
    assert manifest["dhf_hash"] in html and manifest["approvers_hash"] in html
    for code, entry in manifest["documents"].items():
        assert entry["file"] in html and entry["file_hash"] in html and entry["hash"] in html, code
    for who, record in records.items():
        assert who in html and record in html and _fingerprint(project, who) in html
    assert "I have reviewed the changes to these documents and approve them for release." in html
    assert "Verified" in html


@pytest.mark.dhf_links("SRS-067")
@pytest.mark.dhf_testing("T2")
def test_a_signature_without_proven_presence_is_marked_on_the_sheet(project: Project) -> None:
    _sign_all(project)

    result, report = _sheet(project)

    assert result.exit_code == 0
    assert "signed without proven presence" in (project.root / "sheet" / "approval-sheet.html").read_text()
    assert len(report.warnings) == 4 and all("no_touch_required" in w for w in report.warnings)


@pytest.mark.dhf_links("SRS-067")
@pytest.mark.dhf_testing("T3")
def test_a_document_nobody_owns_needs_no_signature_and_shows_none(project: Project) -> None:
    _sign_all(project)

    _sheet(project)

    html = (project.root / "sheet" / "approval-sheet.html").read_text()
    assert "no role: no signature is required" in html


@pytest.mark.dhf_links("SRS-067")
@pytest.mark.dhf_testing("T4")
def test_the_sheet_lists_the_approvers_list_the_release_pins(project: Project) -> None:
    _sign_all(project)

    _sheet(project)

    html = (project.root / "sheet" / "approval-sheet.html").read_text()
    section = html.split("Approvers</h2>")[1]
    for who in ("Lead", "Pat", "Sam", "Quinn"):
        assert _fingerprint(project, who) in section
    assert "software-lead" in section and "product-manager, risk-manager" in section


@pytest.mark.dhf_links("SRS-066")
@pytest.mark.dhf_testing("T2")
def test_a_release_edited_after_it_was_signed_gets_no_sheet(project: Project) -> None:
    _sign_all(project)
    project.edit("SRS-001", title="changed after signing")

    result, report = _sheet(project)

    assert result.exit_code == 1 and report.path is None
    assert any("SRS-001" in e for e in report.errors)


@pytest.mark.dhf_links("SRS-066")
@pytest.mark.dhf_testing("T3")
def test_a_project_without_approvers_cannot_have_a_sheet(tmp_path: Path) -> None:
    project = build_project(tmp_path, with_approvers=False)
    project.ready_to_release()
    project.release()

    result, report = _sheet(project)

    assert result.exit_code == 1 and report.path is None
    assert "not configured" in report.errors[0]


@pytest.mark.dhf_links("SRS-066")
@pytest.mark.dhf_testing("T4")
def test_a_bad_version_is_refused_before_anything_runs(project: Project) -> None:
    result = project.run("build", "approvals", "--release", "../x", "--out-dir", str(project.root / "sheet"))

    assert result.exit_code == 2 and "Invalid value" in result.stderr


def test_every_specification_points_to_the_sheet_when_there_is_an_approvers_list(project: Project) -> None:
    specs = sorted((project.root / "rel" / "1.0.0" / "specifications").glob("*.html"))

    assert specs
    assert all(LINE in path.read_text() for path in specs), [p.name for p in specs if LINE not in p.read_text()]


def test_a_specification_says_nothing_of_approval_without_an_approvers_list(tmp_path: Path) -> None:
    project = build_project(tmp_path, with_approvers=False)
    project.ready_to_release()
    project.release()

    specs = sorted((project.root / "rel" / "1.0.0" / "specifications").glob("*.html"))

    assert specs and not any("approval sheet" in path.read_text() for path in specs)


@pytest.mark.skipif(not REQUIRED and not _pdf_libraries_load(), reason="WeasyPrint's native libraries are not available")
def test_the_sheet_can_be_a_pdf(project: Project) -> None:
    _sign_all(project)

    result, report = _sheet(project, "--doc-format", "pdf")

    assert result.exit_code == 0, result.stderr
    assert report.path is not None and Path(report.path).read_bytes()[:5] == b"%PDF-"
