"""
API tests for CR-032: PDF submission template validation.

Verifies payload template validation for traceability/compliance report submission
profiles including unknown template handling, report-kind mismatch, required-key
checks, and compliance row field checks.

@links: SYS-011
"""

from compliantflow.pdf_template_validation import validate_submission_payload


def test_TC_SYS_037_001_traceability_payload_passes_for_internal_qms_template() -> None:
    """
    TC-SYS-037-001: Internal QMS traceability profile accepts valid traceability payload.

    @test_id: TC-SYS-037-001
    @links: SYS-011
    """
    payload = {
        "columns": ["CRS", "SYS"],
        "rows": [{"CRS": "CRS-001", "SYS": "SYS-001", "is_complete": True}],
    }

    result = validate_submission_payload(
        payload,
        report_kind="traceability",
        template_key="internal_qms_traceability",
    )

    assert result.is_valid is True
    assert result.issues == ()


def test_TC_SYS_037_002_compliance_payload_fails_for_missing_required_keys() -> None:
    """
    TC-SYS-037-002: Compliance profile rejects payloads missing required top-level keys.

    @test_id: TC-SYS-037-002
    @links: SYS-011
    """
    payload = {
        "score": 95.0,
        "results": [{"policy_id": "IEC-001", "passed": True}],
    }

    result = validate_submission_payload(
        payload,
        report_kind="compliance",
        template_key="fda_510k_compliance",
    )

    assert result.is_valid is False
    assert any(issue.code == "missing_required_key" for issue in result.issues)


def test_TC_SYS_037_003_compliance_payload_fails_for_report_kind_mismatch() -> None:
    """
    TC-SYS-037-003: Compliance profile rejects traceability report_kind.

    @test_id: TC-SYS-037-003
    @links: SYS-011
    """
    payload = {
        "columns": ["CRS", "SYS"],
        "rows": [{"CRS": "CRS-001", "SYS": "SYS-001", "is_complete": True}],
    }

    result = validate_submission_payload(
        payload,
        report_kind="traceability",
        template_key="ce_marking_compliance",
    )

    assert result.is_valid is False
    assert any(issue.code == "report_kind_mismatch" for issue in result.issues)


def test_TC_SYS_037_004_compliance_payload_fails_for_result_row_required_fields() -> None:
    """
    TC-SYS-037-004: Compliance profile enforces required fields within each result row.

    @test_id: TC-SYS-037-004
    @links: SYS-011
    """
    payload = {
        "source_id": "IEC_62304",
        "score": 99.0,
        "total_policies": 2,
        "passed_policies": 1,
        "results": [
            {"policy_id": "IEC-001", "passed": True},
            {"policy_id": "", "details": "missing passed field"},
        ],
    }

    result = validate_submission_payload(
        payload,
        report_kind="compliance",
        template_key="fda_510k_compliance",
    )

    assert result.is_valid is False
    codes = {issue.code for issue in result.issues}
    assert "missing_required_result_field" in codes
    assert "empty_required_result_field" in codes


def test_TC_SYS_037_005_payload_fails_for_unknown_template() -> None:
    """
    TC-SYS-037-005: Validator rejects unknown template profile IDs.

    @test_id: TC-SYS-037-005
    @links: SYS-011
    """
    payload = {"columns": ["CRS"], "rows": [{"CRS": "CRS-001"}]}

    result = validate_submission_payload(
        payload,
        report_kind="traceability",
        template_key="not_real",
    )

    assert result.is_valid is False
    assert len(result.issues) == 1
    assert result.issues[0].code == "unknown_template"


def test_TC_SYS_037_006_compliance_payload_fails_when_results_is_not_a_list() -> None:
    """
    TC-SYS-037-006: Compliance profile requires results to be a list.

    @test_id: TC-SYS-037-006
    @links: SYS-011
    """
    payload = {
        "source_id": "IEC_62304",
        "score": 99.0,
        "total_policies": 2,
        "passed_policies": 1,
        "results": "not-a-list",
    }

    result = validate_submission_payload(
        payload,
        report_kind="compliance",
        template_key="fda_510k_compliance",
    )

    assert result.is_valid is False
    assert any(issue.code == "invalid_results_type" for issue in result.issues)
