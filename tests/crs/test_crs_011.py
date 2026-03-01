"""
API tests for CRS-011: Regulatory Compliance Validation

Verifies regulatory compliance checking through the CompliantFlowCore API.

@links: CRS-011
"""


def test_TC_CRS_011_001_load_policy_group(core):
    """
    TC-CRS-011-001: Load Regulatory Policy Group via API

    @test_id: TC-CRS-011-001
    @links: CRS-011

    get_policy_group('IEC_62304') loads the policy group from the
    governance directory and returns its structure.
    """
    group = core.get_policy_group("IEC_62304")

    assert group is not None, "Expected IEC_62304 policy group to be loadable"
    assert isinstance(group, dict)
    assert group.get("id") == "IEC_62304"
    assert "policies" in group or "title" in group, \
        f"Expected policy group structure, got: {list(group.keys())}"


def test_TC_CRS_011_002_run_compliance_check(core):
    """
    TC-CRS-011-002: Run IEC 62304 Compliance Check via API

    @test_id: TC-CRS-011-002
    @links: CRS-011

    check_compliance('IEC_62304') evaluates each policy against the
    current DHF items and returns a structured report.
    """
    report = core.check_compliance("IEC_62304")

    assert report is not None, "Expected compliance check to return a report"
    assert isinstance(report, dict), "Expected report as dict"

    # The report should contain results for individual policies
    # (structure: depends on PolicyEngine output)
    assert len(report) > 0, "Expected non-empty compliance report"

    # The test fixture includes IEC 62304 policies; report should reference them
    report_str = str(report)
    assert any(term in report_str for term in ["5.1", "5.3", "policy", "IEC", "result", "status"]), \
        f"Report should reference IEC 62304 policy data: {report_str[:200]}"
