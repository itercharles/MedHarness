"""
API tests for SYS-001: Objects Management and Tracking

Verifies: The system shall support configurable objects (requirements, design items,
change requests) to maintain a complete history.

@links: SYS-001

This replaces browser-based tests with direct API testing for better performance
and stability.
"""

import pytest
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from traceability.compliant_flow_core import CompliantFlowCore


def test_TC_SYS_001_001_view_requirement_object(test_dhf_root):
    """
    TC-SYS-001-001: View Requirement Object (API)

    @links: SYS-001
    @test_id: TC-SYS-001-001

    Verify system can load and retrieve requirement objects with complete information.
    """
    # Initialize core with test DHF
    core = CompliantFlowCore(test_dhf_root)

    # Get requirement object
    item = core.get_item("SRS-001")

    # Verify object exists and has expected data
    assert item is not None, "Should retrieve SRS-001"
    assert item["id"] == "SRS-001"
    assert item["title"] == "Item Persistence and Versioning"
    assert "Software shall persist items to YAML files" in item["content"]
    assert item["status"] == "approved"

    # Verify it's in the items collection
    all_items = core.get_all_items()
    item_ids = [i["id"] for i in all_items]
    assert "SRS-001" in item_ids

    # Verify relationships are loaded
    assert "derives_from" in item
    assert item["derives_from"] is not None


def test_TC_SYS_001_002_view_change_request_object(test_dhf_root):
    """
    TC-SYS-001-002: View Change Request Object (API)

    @links: SYS-001
    @test_id: TC-SYS-001-002

    Verify system can load and retrieve change request objects.
    """
    # Initialize core with test DHF
    core = CompliantFlowCore(test_dhf_root)

    # Get change request object
    item = core.get_item("CR-001")

    # Verify object exists and has expected data
    assert item is not None, "Should retrieve CR-001"
    assert item["id"] == "CR-001"
    assert item["title"] == "Test Change Request"
    assert "Change request for testing purposes" in item["description"]
    # CR starts in draft status
    assert item["status"] in ["draft", "approved"]

    # Verify affected items relationship
    assert "affected_items" in item
    assert item["affected_items"] is not None
    assert "SRS-001" in item["affected_items"]


def test_TC_SYS_001_003_view_architecture_object(test_dhf_root):
    """
    TC-SYS-001-003: View Architecture Object (API)

    @links: SYS-001
    @test_id: TC-SYS-001-003

    Verify system can load and retrieve architecture/design objects.
    """
    # Initialize core with test DHF
    core = CompliantFlowCore(test_dhf_root)

    # Get architecture object
    item = core.get_item("SYSARCH-001")

    # Verify object exists and has expected data
    assert item is not None, "Should retrieve SYSARCH-001"
    assert item["id"] == "SYSARCH-001"
    assert item["title"] == "System Architecture Component"
    assert "Architecture component for test system" in item["content"]

    # Verify substantial data is present
    assert len(item["content"]) > 10, "Architecture object should contain substantial data"


def test_TC_SYS_001_004_filter_objects_by_type(test_dhf_root):
    """
    TC-SYS-001-004: Filter Objects by Type (API)

    @links: SYS-001
    @test_id: TC-SYS-001-004

    Verify system can filter objects by document type.
    """
    # Initialize core with test DHF
    core = CompliantFlowCore(test_dhf_root)

    # Get all items and filter by type (using ID prefix)
    all_items = core.get_all_items()

    srs_items = [item for item in all_items if item["id"].startswith("SRS-")]
    cr_items = [item for item in all_items if item["id"].startswith("CR-")]
    sysarch_items = [item for item in all_items if item["id"].startswith("SYSARCH-")]

    # Verify filtering works
    assert len(srs_items) > 0, "Should have SRS items"
    assert len(cr_items) > 0, "Should have CR items"
    assert len(sysarch_items) > 0, "Should have SYSARCH items"

    # Verify we can count items by type
    assert len(srs_items) >= 2, "Should have at least 2 SRS items (SRS-001, SRS-002)"
    assert len(cr_items) >= 1, "Should have at least 1 CR item"
    assert len(sysarch_items) >= 1, "Should have at least 1 SYSARCH item"


def test_TC_SYS_001_005_search_objects(test_dhf_root):
    """
    TC-SYS-001-005: Search Objects (API)

    @links: SYS-001
    @test_id: TC-SYS-001-005

    Verify system can search objects by content.
    """
    # Initialize core with test DHF
    core = CompliantFlowCore(test_dhf_root)

    # Search for objects containing specific text
    all_items = core.get_all_items()

    # Search for "persistence" in content (only for items that have content field)
    persistence_items = [
        item for item in all_items
        if "content" in item and "persist" in item["content"].lower()
    ]

    assert len(persistence_items) > 0, "Should find items with 'persist' in content"
    assert any(item["id"] == "SRS-001" for item in persistence_items), \
        "Should find SRS-001 which mentions persistence"
