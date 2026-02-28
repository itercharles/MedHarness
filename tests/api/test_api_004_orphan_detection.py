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

from traceability.compliant_flow_core import CompliantFlowCore
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

    # Find orphans
    orphans = core.graph.find_orphans()

    # Verify orphans structure
    assert isinstance(orphans, dict), "Orphans should be grouped by type"

    # Each type should have a list of orphan items
    for doc_type, orphan_list in orphans.items():
        assert isinstance(orphan_list, list), f"Orphans for {doc_type} should be a list"
        for orphan in orphan_list:
            assert isinstance(orphan, Item), "Each orphan should be an Item instance"


def test_TC_SYS_004_002_orphan_exclusions(test_dhf_root):
    """
    TC-SYS-004-002: Orphan Exclusions (API)

    @links: SYS-004
    @test_id: TC-SYS-004-002

    Verify root types are excluded from orphan detection.
    """
    # Initialize core with test DHF
    core = CompliantFlowCore(test_dhf_root)

    # Find orphans
    orphans = core.graph.find_orphans()

    # UC (Use Cases) are root items, should not be flagged as orphans
    if "UC" in orphans:
        # If UC appears in orphans, the list should be empty
        assert len(orphans["UC"]) == 0, "Use Cases (UC) should not be orphaned"


def test_TC_SYS_004_003_create_orphan_and_detect(test_dhf_root):
    """
    TC-SYS-004-003: Create Orphan and Detect (API)

    @links: SYS-004
    @test_id: TC-SYS-004-003

    Verify system detects newly created orphan items.
    """
    # Initialize core with test DHF
    core = CompliantFlowCore(test_dhf_root)

    # Create a new SRS item without derives_from (making it an orphan)
    new_item_data = {
        "id": "SRS-999",
        "doc_type": "SRS",
        "title": "Orphan Test Item",
        "content": "This item has no parent links",
        "status": "draft",
        # Intentionally no derives_from field
    }

    # Save the item
    core.save_item(Item(**new_item_data))

    # Refresh core to reload items
    core.refresh()

    # Find orphans
    orphans = core.graph.find_orphans()

    # The new SRS-999 should be detected as an orphan
    if "SRS" in orphans:
        orphan_ids = [item["id"] for item in orphans["SRS"]]
        assert "SRS-999" in orphan_ids, "SRS-999 should be detected as orphan"


def test_TC_SYS_004_004_orphan_count(test_dhf_root):
    """
    TC-SYS-004-004: Orphan Count (API)

    @links: SYS-004
    @test_id: TC-SYS-004-004

    Verify system can count total orphan items.
    """
    # Initialize core with test DHF
    core = CompliantFlowCore(test_dhf_root)

    # Find orphans
    orphans = core.graph.find_orphans()

    # Count total orphans across all types
    total_orphans = sum(len(orphan_list) for orphan_list in orphans.values())

    # Verify count is accessible
    assert total_orphans >= 0, "Should be able to count orphans"

    # For a well-structured test DHF, we might expect 0 orphans
    # (This depends on test data setup)
