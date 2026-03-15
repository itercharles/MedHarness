"""
API tests for CRS-008: Automated Test Integration

Verifies that test coverage and compliance information can be
retrieved through the CompliantFlowCore API.

@links: CRS-008
"""


def test_TC_CRS_008_001_view_requirement_with_traceability(core):
    """
    TC-CRS-008-001: View Requirement with Traceability Data via API

    @test_id: TC-CRS-008-001
    @links: CRS-008

    get_item('SRS-001') returns item data including title and upstream links,
    which serve as the basis for test coverage reporting.
    SRS items use the GitOps approval model — no explicit status field.
    """
    item = core.get_item("SRS-001")

    assert item is not None
    assert item["id"] == "SRS-001"
    assert "Item Persistence and Versioning" in item.get("title", ""), \
        f"Unexpected title: {item.get('title')}"
    # GitOps model: no status field on requirement items
    assert "status" not in item, \
        "SRS items should not have an explicit status field"

    # Traceability is the verification mechanism — check upstream links exist
    chain = core.get_item_chain("SRS-001")
    assert len(chain["nodes"]["SRS-001"]["upstream"]) > 0, \
        "SRS-001 should have upstream links (derives_from SYS-001)"


def test_TC_CRS_008_002_srs_items_have_upstream_traceability(core):
    """
    TC-CRS-008-002: SRS items form a complete upstream traceability chain

    @test_id: TC-CRS-008-002
    @links: CRS-008

    Test Integration requires that software requirements are traceable all the
    way back to system requirements. Every SRS item must have at least one
    upstream SYS item.
    """
    all_srs = [i for i in core.get_all_items() if i["id"].startswith("SRS-")]
    assert len(all_srs) > 0, "Expected at least one SRS item in the fixture"

    for srs_item in all_srs:
        chain = core.get_item_chain(srs_item["id"])
        upstream = chain["nodes"][srs_item["id"]]["upstream"]
        sys_parents = [uid for uid in upstream if uid.startswith("SYS-")]
        assert len(sys_parents) > 0, \
            f"{srs_item['id']} must trace to a SYS item; upstream: {upstream}"
