"""
API tests for CRS-005: Architecture Definition

Verifies system architecture item management through the
CompliantFlowCore API.

@links: CRS-005
"""


def test_TC_CRS_005_001_create_architecture_item(core):
    """
    TC-CRS-005-001: Create Architecture Item via API

    @test_id: TC-CRS-005-001
    @links: CRS-005

    create_item() with type 'SYSARCH' persists a new architecture
    item and returns an assigned ID with the correct prefix.
    """
    item_data = {
        "type": "SYSARCH",
        "title": "Test Architecture Component",
        "content": "Architecture component created via API test",
    }
    created = core.create_item(item_data)

    assert created is not None
    assert "id" in created
    assert created["id"].startswith("SYSARCH-"), \
        f"Expected SYSARCH- prefix, got {created['id']}"
    assert created.get("title") == "Test Architecture Component"

    # Verify it can be retrieved
    fetched = core.get_item(created["id"])
    assert fetched is not None
    assert fetched["id"] == created["id"]


def test_TC_CRS_005_002_view_architecture_item(core):
    """
    TC-CRS-005-002: View Architecture Item Details via API

    @test_id: TC-CRS-005-002
    @links: CRS-005

    get_item('SYSARCH-001') returns the architecture item with all
    expected fields populated.
    """
    item = core.get_item("SYSARCH-001")

    assert item is not None
    assert item["id"] == "SYSARCH-001"
    assert "title" in item
    assert "System Architecture Component" in item.get("title", "")


def test_TC_CRS_005_003_architecture_item_approved_status(core):
    """
    TC-CRS-005-003: Architecture Item Has Approved Status via API

    @test_id: TC-CRS-005-003
    @links: CRS-005

    The SYSARCH-001 fixture item has status 'approved', representing
    a lifecycle-approved architecture decision.
    """
    item = core.get_item("SYSARCH-001")

    assert item is not None
    assert item.get("status") == "approved", \
        f"Expected SYSARCH-001 to be 'approved', got '{item.get('status')}'"
