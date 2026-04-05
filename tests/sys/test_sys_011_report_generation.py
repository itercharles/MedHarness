"""
Tests for SYS-011: PDF Evidence Report Generation

Verifies the report generator renders traceability and compliance reports
to caller-specified output paths without mutating the DHF.

@links: SYS-011
"""

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
