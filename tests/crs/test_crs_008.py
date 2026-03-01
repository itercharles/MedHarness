"""
API tests for CRS-008: Automated Test Integration

Verifies that test coverage and compliance information can be
retrieved through the CompliantFlowCore API.

@links: CRS-008
"""


def test_TC_CRS_008_001_view_requirement_with_verification_data(core):
    """
    TC-CRS-008-001: View Requirement with Verification Data via API

    @test_id: TC-CRS-008-001
    @links: CRS-008

    get_item('SRS-001') returns item data including title and status,
    which serve as the basis for test coverage reporting.
    """
    item = core.get_item("SRS-001")

    assert item is not None
    assert item["id"] == "SRS-001"
    assert "Item Persistence and Versioning" in item.get("title", ""), \
        f"Unexpected title: {item.get('title')}"
    assert item.get("status") == "approved"

    # Traceability is the verification mechanism — check upstream links exist
    neighbors = core.get_item_neighbors("SRS-001")
    assert len(neighbors.get("upstream", [])) > 0, \
        "SRS-001 should have upstream links (derives_from SYS-001)"


def test_TC_CRS_008_002_check_compliance_report(core):
    """
    TC-CRS-008-002: Generate Compliance Report via API

    @test_id: TC-CRS-008-002
    @links: CRS-008

    check_compliance('IEC_62304') returns a structured compliance report
    including policy evaluation results.
    """
    report = core.check_compliance("IEC_62304")

    assert report is not None, "Expected a compliance report for IEC_62304"
    assert isinstance(report, dict), "Expected compliance report as dict"
    # Report should contain policy evaluation data
    assert len(report) > 0, "Expected non-empty compliance report"
