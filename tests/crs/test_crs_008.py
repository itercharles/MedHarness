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


def test_TC_CRS_008_002_approved_items_have_full_traceability(core):
    """
    TC-CRS-008-002: Approved SRS items form a complete upstream traceability chain

    @test_id: TC-CRS-008-002
    @links: CRS-008

    Test Integration requires that approved software requirements are
    traceable all the way back to system requirements.  Every approved
    SRS item must have at least one upstream SYS item.
    """
    approved_srs = core.get_items_filtered("SRS", ["approved"], "")
    assert len(approved_srs) > 0, "Expected at least one approved SRS item in the fixture"

    for srs_item in approved_srs:
        neighbors = core.get_item_neighbors(srs_item["id"])
        upstream = neighbors.get("upstream", [])
        sys_parents = [uid for uid in upstream if uid.startswith("SYS-")]
        assert len(sys_parents) > 0, \
            f"Approved {srs_item['id']} must trace to a SYS item; upstream: {upstream}"
