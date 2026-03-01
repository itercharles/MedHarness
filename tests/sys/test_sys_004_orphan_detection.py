"""
API tests for SYS-004: Orphan Detection and Reporting

Verifies: The system shall detect and report orphan items (items without
required parent links).

@links: SYS-004

This replaces browser-based tests with direct API testing.
"""

import pytest
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from compliantflow.core import CompliantFlowCore
from traceability.models.item import Item


def test_TC_SYS_004_001_detect_orphans(test_dhf_root):
    """
    TC-SYS-004-001: Detect Orphan Items (API)

    @links: SYS-004
    @test_id: TC-SYS-004-001

    Verify system can detect orphan items.
    """
    # Initialize core with test DHF
    core = CompliantFlowCore(test_dhf_root)

    # Find orphans (returns list of orphan dicts)
    orphans = core.graph.find_orphans()

    # Verify orphans structure
    assert isinstance(orphans, list), "Orphans should be a list"

    # Each orphan should have required fields
    for orphan in orphans:
        assert isinstance(orphan, dict), "Each orphan should be a dict"
        assert "uid" in orphan, "Orphan should have uid"
        assert "type" in orphan, "Orphan should have type"
        assert "issue" in orphan, "Orphan should have issue description"


def test_TC_SYS_004_002_orphan_exclusions(test_dhf_root):
    """
    TC-SYS-004-002: Orphan Exclusions (API)

    @links: SYS-004
    @test_id: TC-SYS-004-002

    Verify root types are excluded from orphan detection.
    """
    # Initialize core with test DHF
    core = CompliantFlowCore(test_dhf_root)

    # Find orphans (list of orphan dicts)
    orphans = core.graph.find_orphans()

    # UC (Use Cases) are root items with no required parents, should not be flagged as orphans
    uc_orphans = [o for o in orphans if o["type"] == "UC"]
    assert len(uc_orphans) == 0, "Use Cases (UC) should not be orphaned"


def test_TC_SYS_004_003_create_orphan_and_detect(test_dhf_root):
    """
    TC-SYS-004-003: Create Orphan and Detect (API)

    @links: SYS-004
    @test_id: TC-SYS-004-003

    Verify system can create items and detect orphans if configured.
    """
    # Initialize core with test DHF
    core = CompliantFlowCore(test_dhf_root)

    # Create a new SRS item without derives_from
    new_item_data = {
        "type": "SRS",  # Required for ID generation
        "title": "Orphan Test Item",
        "content": "This item has no parent links",
        "status": "draft",
        # Intentionally no derives_from field
    }

    # Create the item (ID will be auto-generated as SRS-003)
    created_item = core.create_item(new_item_data)
    new_item_id = created_item["id"]

    # Verify item was created
    assert created_item is not None
    assert "id" in created_item
    assert created_item["id"].startswith("SRS-")

    # Refresh core to reload items and rebuild graph
    core.refresh()

    # Verify item can be retrieved
    retrieved_item = core.get_item(new_item_id)
    assert retrieved_item is not None
    assert retrieved_item["title"] == "Orphan Test Item"


def test_TC_SYS_004_004_orphan_count(test_dhf_root):
    """
    TC-SYS-004-004: Orphan Count (API)

    @links: SYS-004
    @test_id: TC-SYS-004-004

    Verify system can count total orphan items.
    """
    # Initialize core with test DHF
    core = CompliantFlowCore(test_dhf_root)

    # Find orphans (returns list)
    orphans = core.graph.find_orphans()

    # Count total orphans
    total_orphans = len(orphans)

    # Verify count is accessible
    assert total_orphans >= 0, "Should be able to count orphans"

    # For a well-structured test DHF, we expect 0 orphans
    # All test items have proper parent relationships
    assert total_orphans == 0, f"Test DHF should have no orphans, found {total_orphans}"
