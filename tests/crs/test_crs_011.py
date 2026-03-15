"""
API tests for CRS-011: Regulatory Compliance Validation

Verifies regulatory compliance checking through the CompliantFlowCore API.

@links: CRS-011
"""


def test_TC_CRS_011_001_policy_group_contains_required_sections(core, governance_dir):
    """
    TC-CRS-011-001: IEC 62304 Policy Group Contains Expected Section IDs

    @test_id: TC-CRS-011-001
    @links: CRS-011

    Regulatory Compliance Validation requires that the IEC 62304 policy
    group contains the specific section IDs mandated by the standard.
    The test fixture defines sections 5.1.1, 5.1.3, 5.3.1, 5.5.2, 6.2.1.
    """
    group = core.get_policy_group("IEC_62304", governance_dir)

    assert group is not None, "Expected IEC_62304 policy group to be loadable"

    policies = group.get("policies", [])
    assert len(policies) > 0, "IEC_62304 policy group must contain policies"

    policy_ids = {p.get("id") or p.get("section") for p in policies}
    required_sections = {"5.1.1", "5.3.1", "6.2.1"}
    missing = required_sections - policy_ids
    assert not missing, \
        f"IEC_62304 policy group missing required sections: {missing}"


def test_TC_CRS_011_002_run_compliance_check(core, governance_dir):
    """
    TC-CRS-011-002: Run IEC 62304 Compliance Check via API

    @test_id: TC-CRS-011-002
    @links: CRS-011

    check_compliance('IEC_62304') evaluates each policy against the
    current DHF items and returns a structured report.
    """
    report = core.check_compliance("IEC_62304", governance_dir)

    assert report is not None, "Expected compliance check to return a report"
    assert isinstance(report, dict), "Expected report as dict"

    assert len(report) > 0, "Expected non-empty compliance report"

    report_str = str(report)
    assert any(term in report_str for term in ["5.1", "5.3", "policy", "IEC", "result", "status"]), \
        f"Report should reference IEC 62304 policy data: {report_str[:200]}"
