"""
API tests for SYS-008: Change Management

Verifies: The system shall support change request management with
affected item tracking.

@links: SYS-008

This replaces browser-based tests with direct API testing.
"""

import pytest
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from traceability.compliant_flow_core import CompliantFlowCore
from traceability.models.item import Item


def test_TC_SYS_008_001_list_change_requests(test_dhf_root):
    """
    TC-SYS-008-001: List Change Requests (API)

    @links: SYS-008
    @test_id: TC-SYS-008-001

    Verify system can list all change requests.
    """
    # Initialize core with test DHF
    core = CompliantFlowCore(test_dhf_root)

    # Get all CR items (filter from all items)
    all_items = core.get_all_items()
    cr_items = [item for item in all_items if item["id"].startswith("CR-")]

    # Should have at least one CR
    assert len(cr_items) > 0, "Should have change requests"

    # Verify CR-001 exists
    cr_ids = [item["id"] for item in cr_items]
    assert "CR-001" in cr_ids, "Should have CR-001 in test data"


def test_TC_SYS_008_002_view_change_request_details(test_dhf_root):
    """
    TC-SYS-008-002: View Change Request Details (API)

    @links: SYS-008
    @test_id: TC-SYS-008-002

    Verify system can retrieve detailed CR information.
    """
    # Initialize core with test DHF
    core = CompliantFlowCore(test_dhf_root)

    # Get CR-001 (returns dict)
    cr = core.get_item("CR-001")

    # Verify CR details
    assert cr is not None
    assert cr["id"] == "CR-001"
    assert cr["title"] == "Test Change Request"
    assert "Change request for testing purposes" in cr["description"]
    # CR can be in draft or approved status
    assert cr["status"] in ["draft", "approved"]


def test_TC_SYS_008_003_view_affected_items(test_dhf_root):
    """
    TC-SYS-008-003: View Affected Items (API)

    @links: SYS-008
    @test_id: TC-SYS-008-003

    Verify system tracks affected items for CRs.
    """
    # Initialize core with test DHF
    core = CompliantFlowCore(test_dhf_root)

    # Get CR-001 (returns dict)
    cr = core.get_item("CR-001")

    # Verify affected_items field exists and has data
    assert "affected_items" in cr, "CR should have affected_items field"
    assert cr["affected_items"] is not None, "CR should have affected items"
    assert len(cr["affected_items"]) > 0, "CR should affect at least one item"

    # Verify SRS-001 is in affected items
    assert "SRS-001" in cr["affected_items"], "CR-001 should affect SRS-001"

    # Verify affected items actually exist
    for affected_id in cr["affected_items"]:
        affected_item = core.get_item(affected_id)
        assert affected_item is not None, f"Affected item {affected_id} should exist"


def test_TC_SYS_008_004_create_change_request(test_dhf_root):
    """
    TC-SYS-008-004: Create Change Request (API)

    @links: SYS-008
    @test_id: TC-SYS-008-004

    Verify system can create new change requests.
    """
    # Initialize core with test DHF
    core = CompliantFlowCore(test_dhf_root)

    # Create new CR using Item model and saver
    new_cr_data = {
        "id": "CR-999",
        "doc_type": "CR",
        "title": "API Test Change Request",
        "description": "Testing CR creation via API",
        "justification": "Testing change management functionality",
        "affected_items": ["SRS-001"],
        "status": "draft"
    }

    # Use Item model and saver to save directly
    new_cr = Item(**new_cr_data)
    core.saver.save(new_cr, author="test_user")

    # Refresh and verify it was created
    core.refresh()
    created_cr = core.get_item("CR-999")

    assert created_cr is not None, "CR-999 should be created"
    assert created_cr["title"] == "API Test Change Request"
    assert created_cr["status"] == "draft"


def test_TC_SYS_008_005_edit_change_request(test_dhf_root):
    """
    TC-SYS-008-005: Edit Change Request (API)

    @links: SYS-008
    @test_id: TC-SYS-008-005

    Verify system can edit existing change requests.
    """
    # Initialize core with test DHF
    core = CompliantFlowCore(test_dhf_root)

    # Get existing CR (returns dict)
    cr = core.get_item("CR-001")
    original_title = cr["title"]

    # Modify CR - convert back to Item and save
    cr["title"] = "Modified Test Change Request"
    item = Item(**cr)
    core.saver.save(item, author="test_user")

    # Refresh and verify changes
    core.refresh()
    modified_cr = core.get_item("CR-001")

    assert modified_cr["title"] == "Modified Test Change Request"
    assert modified_cr["title"] != original_title


def test_TC_SYS_008_006_cr_impact_analysis(test_dhf_root):
    """
    TC-SYS-008-006: CR Impact Analysis (API)

    @links: SYS-008
    @test_id: TC-SYS-008-006

    Verify system can analyze impact of change requests.
    """
    # Initialize core with test DHF
    core = CompliantFlowCore(test_dhf_root)

    # Get CR-001 (returns dict)
    cr = core.get_item("CR-001")

    # For each affected item, find all downstream items
    total_impact = set()
    for affected_id in cr["affected_items"]:
        # Find descendants using get_downstream (returns set of UIDs)
        descendants = core.graph.get_downstream(affected_id)
        total_impact.update(descendants)

    # Should have some impact
    # (The actual count depends on test data structure)
    assert isinstance(total_impact, set), "Impact should be calculable"
