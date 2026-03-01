"""
API tests for CRS-001: Requirement Definition

Verifies that items can be created, retrieved, and filtered
through the CompliantFlowCore API.

@links: CRS-001
"""


def test_TC_CRS_001_001_create_requirement(core):
    """
    TC-CRS-001-001: Create New Requirement via API

    @test_id: TC-CRS-001-001
    @links: CRS-001

    CompliantFlowCore.create_item() persists a new SRS item and
    returns its assigned ID.
    """
    item_data = {
        "type": "SRS",
        "title": "Test Requirement",
        "content": "This is a test requirement created via API test",
    }
    created = core.create_item(item_data)

    assert created is not None
    assert "id" in created
    assert created["id"].startswith("SRS-"), f"Expected SRS- prefix, got {created['id']}"
    assert created.get("title") == "Test Requirement"

    # Verify it can be retrieved
    fetched = core.get_item(created["id"])
    assert fetched is not None
    assert fetched["id"] == created["id"]


def test_TC_CRS_001_002_view_requirement_details(core):
    """
    TC-CRS-001-002: View Requirement Details via API — traceability chain intact

    @test_id: TC-CRS-001-002
    @links: CRS-001

    get_item() returns the item together with its derives_from links.
    Requirement Definition means requirements must be traceable upward;
    SRS-001 must link to a SYS parent via derives_from.
    """
    item = core.get_item("SRS-001")

    assert item is not None
    assert item["id"] == "SRS-001"

    # The derives_from field must be populated — requirement is traceable
    derives_from = item.get("derives_from") or item.get("all_linked_uids") or []

    assert len(derives_from) > 0, \
        "SRS-001 must have a parent requirement (derives_from) for traceability"
    assert any("SYS-" in uid for uid in derives_from), \
        f"SRS-001 should derive from a SYS item; got: {derives_from}"


def test_TC_CRS_001_003_search_requirements(core):
    """
    TC-CRS-001-003: Search Requirements via API

    @test_id: TC-CRS-001-003
    @links: CRS-001

    get_items_filtered() with a search string returns only matching items.
    """
    # Search by partial title keyword
    results = core.get_items_filtered("SRS", None, "Graph")
    assert len(results) >= 1, "Expected at least one SRS item matching 'Graph'"
    assert all("SRS-" in item["id"] for item in results)

    # Retrieve a specific item by ID lookup
    item = core.get_item("SRS-002")
    assert item is not None
    assert item["id"] == "SRS-002"
