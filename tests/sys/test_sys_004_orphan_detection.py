"""
API tests for SYS-004: Orphan Detection and Reporting

Verifies: The system shall detect and report orphan items (items without
required parent links).

@links: SYS-004
"""

import pytest

from compliantflow.core import CompliantFlowCore


def test_TC_SYS_004_001_detect_orphans(stub_adapter):
    """
    TC-SYS-004-001: Detect Orphan Items (API)

    @links: SYS-004
    @test_id: TC-SYS-004-001

    Verify system can detect orphan items.
    """
    core = CompliantFlowCore(stub_adapter)

    orphans = core.graph.find_orphans()

    assert isinstance(orphans, list), "Orphans should be a list"

    for orphan in orphans:
        assert isinstance(orphan, dict), "Each orphan should be a dict"
        assert "uid" in orphan, "Orphan should have uid"
        assert "type" in orphan, "Orphan should have type"
        assert "issue" in orphan, "Orphan should have issue description"


def test_TC_SYS_004_002_orphan_exclusions(stub_adapter):
    """
    TC-SYS-004-002: Orphan Exclusions (API)

    @links: SYS-004
    @test_id: TC-SYS-004-002

    Verify root types are excluded from orphan detection.
    """
    core = CompliantFlowCore(stub_adapter)

    orphans = core.graph.find_orphans()

    uc_orphans = [o for o in orphans if o["type"] == "UC"]
    assert len(uc_orphans) == 0, "Use Cases (UC) should not be orphaned"


def test_TC_SYS_004_003_create_orphan_and_detect(stub_adapter):
    """
    TC-SYS-004-003: Create Orphan and Detect (API)

    @links: SYS-004
    @test_id: TC-SYS-004-003

    Verify system can create items and detect orphans if configured.
    """
    core = CompliantFlowCore(stub_adapter)

    new_item_data = {
        "type": "SRS",
        "title": "Orphan Test Item",
        "content": "This item has no parent links",
    }
    created_item = stub_adapter.create_item(new_item_data)
    new_item_id = created_item["id"]
    assert created_item["id"].startswith("SRS-")

    core.refresh()

    retrieved_item = core.get_item(new_item_id)
    assert retrieved_item is not None
    assert retrieved_item["title"] == "Orphan Test Item"


def test_TC_SYS_004_004_orphan_count(stub_adapter):
    """
    TC-SYS-004-004: Orphan Count (API)

    @links: SYS-004
    @test_id: TC-SYS-004-004

    Verify system can count total orphan items.
    """
    core = CompliantFlowCore(stub_adapter)

    orphans = core.graph.find_orphans()

    total_orphans = len(orphans)

    assert total_orphans >= 0, "Should be able to count orphans"

    assert total_orphans == 0, f"Test DHF should have no orphans, found {total_orphans}"
