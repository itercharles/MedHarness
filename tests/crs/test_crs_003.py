"""
API tests for CRS-003: Change Control

Verifies change control workflow through the CompliantFlowCore API.

@links: CRS-003
"""


def test_TC_CRS_003_001_view_change_requests(core):
    """
    TC-CRS-003-001: List Change Requests via API

    @test_id: TC-CRS-003-001
    @links: CRS-003

    get_items_filtered('CR') returns all change request items.
    The test fixture creates CR-001.
    """
    cr_items = core.get_items_filtered("CR", None, "")

    assert len(cr_items) >= 1, "Expected at least one CR item (CR-001 from fixture)"
    for item in cr_items:
        assert item["id"].startswith("CR-"), f"Expected CR- prefix, got {item['id']}"


def test_TC_CRS_003_002_create_change_request(core):
    """
    TC-CRS-003-002: Create Change Request via API

    @test_id: TC-CRS-003-002
    @links: CRS-003

    create_item() with CR data persists a new change request and
    assigns it an ID starting with CR-.
    """
    item_data = {
        "type": "CR",
        "title": "Test Change Request",
        "description": "Test change request created via API test",
        "justification": "API test validation",
    }
    created = core.create_item(item_data)

    assert created is not None
    assert "id" in created
    assert created["id"].startswith("CR-"), f"Expected CR- prefix, got {created['id']}"
    assert created.get("title") == "Test Change Request"

    # Verify it is retrievable
    fetched = core.get_item(created["id"])
    assert fetched is not None
    assert fetched["id"] == created["id"]
