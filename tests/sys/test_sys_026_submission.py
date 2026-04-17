"""
API tests for CR-047: 510(k) Submission Evidence Package.

Verifies that assemble_submission:
  1. Blocks assembly when compliance gate fails (no --force)
  2. Proceeds with --force even when gate fails
  3. Produces a ZIP containing all 7 required artifacts when gate passes
  4. Cover document contains FDA eSTAR section references

@links: SYS-026
"""

import zipfile
from pathlib import Path

import pytest

from compliantflow.core import CompliantFlowCore
from compliantflow.submission import assemble_submission, SubmissionGateError


def _make_core(stub_adapter):
    return CompliantFlowCore(stub_adapter)


def _fake_to_pdf(monkeypatch):
    """Patch _to_pdf to write a minimal stub PDF instead of invoking WeasyPrint."""
    from compliantflow import report_generator

    def _stub(html: str, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"%PDF-1.4 stub\n")

    monkeypatch.setattr(report_generator, "_to_pdf", _stub)


def _passing_governance_dir(tmp_path: Path) -> Path:
    """Governance dir whose checks all pass against the standard test dataset."""
    from tests.fixtures.test_data import populate_governance
    gov_dir = tmp_path / "governance"
    populate_governance(gov_dir)
    return gov_dir


def _failing_governance_dir(tmp_path: Path) -> Path:
    """Governance dir with a policy that always fails."""
    import yaml
    gov_dir = tmp_path / "governance_fail"
    gov_dir.mkdir(parents=True)
    policy = {
        "id": "FAILING_STANDARD",
        "title": "Always Failing Standard",
        "type": "standard",
        "version": "1.0",
        "policies": [
            {
                "id": "F.1",
                "section": "F.1",
                "text": "This check always fails.",
                "status": "approved",
                "automation": {
                    "check": "attribute_value",
                    "params": {
                        "type_code": "UC",
                        "attribute": "nonexistent_field",
                        "expected_value": "impossible_value",
                    },
                },
            }
        ],
    }
    with open(gov_dir / "FAILING_STANDARD.yaml", "w") as f:
        yaml.dump(policy, f)
    return gov_dir


# ---------------------------------------------------------------------------
# TC-SYS-026-001: completeness gate blocks assembly on failure
# ---------------------------------------------------------------------------

def test_TC_SYS_026_001_gate_blocks_when_compliance_fails(
    stub_adapter, tmp_path, monkeypatch
):
    """
    TC-SYS-026-001: assemble_submission raises SubmissionGateError when a
    compliance check fails and force=False.

    @test_id: TC-SYS-026-001
    @links: SYS-026
    """
    _fake_to_pdf(monkeypatch)
    core = _make_core(stub_adapter)
    gov_dir = _failing_governance_dir(tmp_path)

    with pytest.raises(SubmissionGateError) as exc_info:
        assemble_submission(core, gov_dir, tmp_path / "out", force=False)

    assert "FAILING_STANDARD" in str(exc_info.value)


# ---------------------------------------------------------------------------
# TC-SYS-026-002: --force bypasses the gate
# ---------------------------------------------------------------------------

def test_TC_SYS_026_002_force_bypasses_gate(stub_adapter, tmp_path, monkeypatch):
    """
    TC-SYS-026-002: assemble_submission produces a ZIP when force=True even
    when a compliance check fails.

    @test_id: TC-SYS-026-002
    @links: SYS-026
    """
    _fake_to_pdf(monkeypatch)
    core = _make_core(stub_adapter)
    gov_dir = _failing_governance_dir(tmp_path)
    out_dir = tmp_path / "out"

    zip_path = assemble_submission(core, gov_dir, out_dir, force=True)

    assert zip_path.exists()
    assert zip_path.suffix == ".zip"


# ---------------------------------------------------------------------------
# TC-SYS-026-003: ZIP contains all required artifacts
# ---------------------------------------------------------------------------

def test_TC_SYS_026_003_zip_contains_all_required_artifacts(
    stub_adapter, tmp_path, monkeypatch
):
    """
    TC-SYS-026-003: The generated ZIP contains all 7 required artifact files
    when all compliance checks pass.

    @test_id: TC-SYS-026-003
    @links: SYS-026
    """
    _fake_to_pdf(monkeypatch)
    core = _make_core(stub_adapter)
    gov_dir = _passing_governance_dir(tmp_path)
    out_dir = tmp_path / "out"

    zip_path = assemble_submission(core, gov_dir, out_dir, force=True)

    assert zip_path.exists()
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()

    assert "cover_document.pdf" in names
    assert "traceability_report.pdf" in names
    assert "soup_list.pdf" in names
    assert "risk_rcm_summary.pdf" in names
    assert "test_results_summary.pdf" in names
    assert "cr_evidence.pdf" in names
    # At least one compliance_{standard}.pdf
    assert any(n.startswith("compliance_") and n.endswith(".pdf") for n in names)


# ---------------------------------------------------------------------------
# TC-SYS-026-004: cover document references FDA eSTAR sections
# ---------------------------------------------------------------------------

def test_TC_SYS_026_004_cover_document_references_estar_sections(
    stub_adapter, tmp_path, monkeypatch
):
    """
    TC-SYS-026-004: The cover document HTML contains key FDA eSTAR section names.

    @test_id: TC-SYS-026-004
    @links: SYS-026
    """
    from compliantflow import report_generator
    from compliantflow.submission import _cover_html

    html = _cover_html(["IEC_62304", "ISO_14971"], "2026-01-01")

    assert "Software Description" in html
    assert "Risk Management" in html
    assert "SOUP" in html
    assert "Software Testing" in html
    assert "Change Management" in html


# ---------------------------------------------------------------------------
# TC-SYS-026-005: SubmissionGateError lists failing standards
# ---------------------------------------------------------------------------

def test_TC_SYS_026_005_gate_error_lists_failing_standards(
    stub_adapter, tmp_path, monkeypatch
):
    """
    TC-SYS-026-005: SubmissionGateError message names each failing standard.

    @test_id: TC-SYS-026-005
    @links: SYS-026
    """
    _fake_to_pdf(monkeypatch)
    core = _make_core(stub_adapter)
    gov_dir = _failing_governance_dir(tmp_path)

    with pytest.raises(SubmissionGateError) as exc_info:
        assemble_submission(core, gov_dir, tmp_path / "out", force=False)

    error = exc_info.value
    assert len(error.failures) >= 1
    assert error.failures[0]["standard"] == "FAILING_STANDARD"


# ---------------------------------------------------------------------------
# TC-SYS-026-006: ZIP filename includes today's date
# ---------------------------------------------------------------------------

def test_TC_SYS_026_006_zip_filename_includes_date(
    stub_adapter, tmp_path, monkeypatch
):
    """
    TC-SYS-026-006: The generated ZIP filename follows the pattern submission_YYYY-MM-DD.zip.

    @test_id: TC-SYS-026-006
    @links: SYS-026
    """
    import datetime
    import re

    _fake_to_pdf(monkeypatch)
    core = _make_core(stub_adapter)
    gov_dir = _passing_governance_dir(tmp_path)

    zip_path = assemble_submission(core, gov_dir, tmp_path / "out", force=True)

    assert re.match(r"submission_\d{4}-\d{2}-\d{2}\.zip", zip_path.name)
