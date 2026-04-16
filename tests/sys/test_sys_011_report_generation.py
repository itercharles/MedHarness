"""
Tests for SYS-011: PDF Evidence Report Generation and JSON Export

Verifies the report generator renders traceability and compliance reports
to caller-specified output paths without mutating the DHF.

@links: SYS-011
"""

import json
from pathlib import Path

from compliantflow import report_generator


def test_TC_SYS_011_001_traceability_report_writes_to_requested_path(tmp_path, monkeypatch):
    """
    TC-SYS-011-001: generate_traceability_pdf renders a traceability report to the requested path.

    @test_id: TC-SYS-011-001
    @links: SYS-011
    """
    captured = {}

    def _fake_to_pdf(html: str, output_path: Path) -> None:
        captured["html"] = html
        captured["output_path"] = output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr(report_generator, "_to_pdf", _fake_to_pdf)
    out = tmp_path / "reports" / "traceability.pdf"

    report_generator.generate_traceability_pdf(
        {
            "columns": ["CRS", "SYS", "SRS"],
            "rows": [
                {
                    "CRS": "CRS-008",
                    "SYS": "SYS-011",
                    "SRS": "SRS-006",
                    "is_complete": True,
                    "is_orphan": False,
                    "verification_status": "verified",
                }
            ],
            "test_results": {
                "TC-SYS-011-001": {
                    "status": "PASS",
                    "title": "Report output path test",
                    "links": ["SYS-011"],
                    "run_id": "local",
                }
            },
        },
        out,
    )

    assert captured["output_path"] == out
    assert "Traceability Report" in captured["html"]
    assert out.exists()


def test_TC_SYS_011_002_compliance_report_writes_to_requested_path(tmp_path, monkeypatch):
    """
    TC-SYS-011-002: generate_compliance_pdf renders a compliance report to the requested path.

    @test_id: TC-SYS-011-002
    @links: SYS-011
    """
    captured = {}

    def _fake_to_pdf(html: str, output_path: Path) -> None:
        captured["html"] = html
        captured["output_path"] = output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr(report_generator, "_to_pdf", _fake_to_pdf)
    out = tmp_path / "reports" / "compliance.pdf"

    report_generator.generate_compliance_pdf(
        {
            "source_id": "IEC_62304",
            "total_policies": 2,
            "passed_policies": 2,
            "score": 100.0,
            "results": [
                {
                    "policy_id": "5.8.1.a",
                    "policy_text": "Verification activities completed before release.",
                    "passed": True,
                    "details": "All linked SYS items verified.",
                }
            ],
        },
        out,
    )

    assert captured["output_path"] == out
    assert "Compliance Report" in captured["html"]
    assert "IEC_62304" in captured["html"]
    assert out.exists()


def test_TC_SYS_011_003_compliance_json_export_writes_valid_json(tmp_path):
    """
    TC-SYS-011-003: generate_compliance_json writes a readable JSON file with
    schema_version and section fields.

    @test_id: TC-SYS-011-003
    @links: SYS-011
    """
    out = tmp_path / "reports" / "compliance.json"

    report_generator.generate_compliance_json(
        {
            "schema_version": "1.0",
            "source_id": "IEC_62304",
            "total_policies": 1,
            "passed_policies": 1,
            "score": 100.0,
            "results": [
                {
                    "policy_id": "5.1.1.a",
                    "section": "5.1.1",
                    "policy_text": "A software development plan shall be established.",
                    "passed": True,
                    "details": "File found: documents/plans/development_plan.md",
                }
            ],
        },
        out,
    )

    assert out.exists()
    data = json.loads(out.read_text())
    assert data["schema_version"] == "1.0"
    assert data["source_id"] == "IEC_62304"
    assert data["results"][0]["section"] == "5.1.1"


def test_TC_SYS_011_004_policy_result_carries_section(stub_adapter, governance_dir):
    """
    TC-SYS-011-004: check_compliance populates section on every PolicyResult.

    @test_id: TC-SYS-011-004
    @links: SYS-011
    """
    from compliantflow.core import CompliantFlowCore

    core = CompliantFlowCore(stub_adapter)
    report = core.check_compliance("IEC_62304", governance_dir)
    assert report is not None
    for result in report["results"]:
        assert "section" in result, f"section missing on {result['policy_id']}"
        assert isinstance(result["section"], str)


def test_TC_SYS_011_005_compliance_report_has_schema_version(stub_adapter, governance_dir):
    """
    TC-SYS-011-005: check_compliance returns a report with schema_version field.

    @test_id: TC-SYS-011-005
    @links: SYS-011
    """
    from compliantflow.core import CompliantFlowCore

    core = CompliantFlowCore(stub_adapter)
    report = core.check_compliance("IEC_62304", governance_dir)
    assert report is not None
    assert report.get("schema_version") == "1.0"
