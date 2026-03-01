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
    TC-CRS-001-002: View Requirement Details via API

    @test_id: TC-CRS-001-002
    @links: CRS-001

    get_item() returns all relevant fields for a known SRS item.
    """
    item = core.get_item("SRS-001")

    assert item is not None
    assert item["id"] == "SRS-001"
    assert "Item Persistence and Versioning" in item.get("title", "")
    assert item.get("status") == "approved"


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
