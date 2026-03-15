"""
API tests for CRS-005: Architecture Definition

Verifies system architecture item management through the
CompliantFlowCore API.

@links: CRS-005
"""


def test_TC_CRS_005_002_view_architecture_item(core):
    """
    TC-CRS-005-002: Architecture Item has SYS implementation link via API

    @test_id: TC-CRS-005-002
    @links: CRS-005

    Architecture Definition requires that each architecture item
    explicitly implements one or more system requirements.
    SYSARCH-001 must have an 'implements' link pointing to a SYS item.
    """
    item = core.get_item("SYSARCH-001")

    assert item is not None
    assert item["id"] == "SYSARCH-001"

    # Architecture item must implement a SYS requirement
    implements = item.get("implements") or item.get("all_linked_uids") or []

    assert len(implements) > 0, \
        "SYSARCH-001 must implement at least one SYS requirement"
    assert any("SYS-" in uid for uid in implements), \
        f"SYSARCH-001 should implement a SYS item; got: {implements}"


def test_TC_CRS_005_003_architecture_item_exists_with_content(core):
    """
    TC-CRS-005-003: Architecture Item Exists with Content via API

    @test_id: TC-CRS-005-003
    @links: CRS-005

    SYSARCH-001 exists with a title and content. Architecture items use the
    GitOps approval model — no explicit status field; presence on main branch
    indicates approval.
    """
    item = core.get_item("SYSARCH-001")

    assert item is not None
    assert item["id"] == "SYSARCH-001"
    assert item.get("title"), "Architecture item should have a title"
    assert item.get("content"), "Architecture item should have content"
    # No status field — GitOps model
    assert "status" not in item, \
        "SYSARCH items should not carry an explicit status field"
