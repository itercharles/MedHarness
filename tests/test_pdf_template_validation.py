from compliantflow.pdf_template_validation import validate_submission_payload


def test_traceability_payload_passes_510k_template():
    payload = {
        "columns": ["CRS", "SYS", "SRS"],
        "rows": [{"CRS": "CRS-001", "SYS": "SYS-001", "SRS": "SRS-001"}],
    }

    result = validate_submission_payload(
        payload,
        template_id="fda_510k_traceability",
        report_kind="traceability",
    )

    assert result.passed is True
    assert result.issues == []


def test_compliance_payload_fails_on_missing_required_fields():
    payload = {
        "source_id": "IEC_62304",
        "results": [],
    }

    result = validate_submission_payload(
        payload,
        template_id="fda_510k_compliance",
        report_kind="compliance",
    )

    assert result.passed is False
    issue_codes = {i.code for i in result.issues}
    assert "missing_required_key" in issue_codes
    assert "required_key_empty" in issue_codes


def test_template_kind_mismatch_is_reported():
    payload = {
        "columns": ["CRS", "SYS", "SRS"],
        "rows": [{"CRS": "CRS-001"}],
        "test_results": {},
    }

    result = validate_submission_payload(
        payload,
        template_id="ce_marking_traceability",
        report_kind="compliance",
    )

    assert result.passed is False
    assert any(i.code == "report_kind_mismatch" for i in result.issues)


def test_compliance_result_row_requires_policy_id_and_passed():
    payload = {
        "source_id": "ISO_14971",
        "results": [{"policy_text": "Some policy"}],
        "total_policies": 1,
        "passed_policies": 0,
        "score": 0.0,
    }

    result = validate_submission_payload(
        payload,
        template_id="fda_510k_compliance",
        report_kind="compliance",
    )

    assert result.passed is False
    paths = {i.path for i in result.issues}
    assert "results[0].policy_id" in paths
    assert "results[0].passed" in paths


def test_explicit_empty_template_registry_is_respected():
    payload = {
        "columns": ["CRS", "SYS", "SRS"],
        "rows": [{"CRS": "CRS-001", "SYS": "SYS-001", "SRS": "SRS-001"}],
    }

    result = validate_submission_payload(
        payload,
        template_id="fda_510k_traceability",
        report_kind="traceability",
        templates={},
    )

    assert result.passed is False
    assert [issue.code for issue in result.issues] == ["template_not_found"]


def test_compliance_result_row_reports_scalar_entries_without_crashing():
    payload = {
        "source_id": "ISO_14971",
        "results": [1],
        "total_policies": 1,
        "passed_policies": 0,
        "score": 0.0,
    }

    result = validate_submission_payload(
        payload,
        template_id="fda_510k_compliance",
        report_kind="compliance",
    )

    assert result.passed is False
    assert any(issue.code == "invalid_result_row" for issue in result.issues)
    assert any(issue.path == "results[0]" for issue in result.issues)
