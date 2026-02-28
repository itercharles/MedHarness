"""
API tests for SYS-003: Visual Traceability

Verifies: The system shall provide visual traceability between requirements,
design items, and test cases.

@links: SYS-003

This replaces browser-based tests with direct API testing.
"""

import pytest
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from traceability.compliant_flow_core import CompliantFlowCore


def test_TC_SYS_003_001_traceability_matrix_data(test_dhf_root):
    """
    TC-SYS-003-001: Traceability Matrix Data (API)

    @links: SYS-003
    @test_id: TC-SYS-003-001

    Verify system can generate traceability matrix data.
    """
    # Initialize core with test DHF
    core = CompliantFlowCore(test_dhf_root)

    # Get all items
    all_items = core.get_all_items()

    # Verify we have items of different types for traceability
    item_types = set(item.doc_type for item in all_items.values())

    assert "UC" in item_types, "Should have Use Case items"
    assert "CRS" in item_types, "Should have Customer Requirement items"
    assert "SYS" in item_types, "Should have System Requirement items"
    assert "SRS" in item_types, "Should have Software Requirement items"

    # Verify specific test items exist
    assert "UC-001" in all_items
    assert "CRS-001" in all_items
    assert "SYS-001" in all_items
    assert "SRS-001" in all_items


def test_TC_SYS_003_002_traceability_graph(test_dhf_root):
    """
    TC-SYS-003-002: Traceability Graph (API)

    @links: SYS-003
    @test_id: TC-SYS-003-002

    Verify system can build a traceability graph.
    """
    # Initialize core with test DHF
    core = CompliantFlowCore(test_dhf_root)

    # Access the graph engine
    graph = core.graph

    # Verify graph has nodes
    assert graph.graph.number_of_nodes() > 0, "Graph should have nodes"
    assert graph.graph.number_of_edges() > 0, "Graph should have edges (relationships)"

    # Verify specific items are in graph
    assert graph.graph.has_node("UC-001")
    assert graph.graph.has_node("CRS-001")
    assert graph.graph.has_node("SYS-001")
    assert graph.graph.has_node("SRS-001")


def test_TC_SYS_003_003_traceability_relationships(test_dhf_root):
    """
    TC-SYS-003-003: Traceability Relationships (API)

    @links: SYS-003
    @test_id: TC-SYS-003-003

    Verify system correctly tracks relationships between items.
    """
    # Initialize core with test DHF
    core = CompliantFlowCore(test_dhf_root)

    # Get SRS-001 and verify its relationships
    srs_item = core.get_item("SRS-001")

    # SRS-001 should derive from SYS items
    assert hasattr(srs_item, 'derives_from')
    assert srs_item.derives_from is not None
    assert len(srs_item.derives_from) > 0

    # Get SYS-001 and verify it derives from CRS
    sys_item = core.get_item("SYS-001")
    assert hasattr(sys_item, 'derives_from')
    assert sys_item.derives_from is not None


def test_TC_SYS_003_004_downstream_traceability(test_dhf_root):
    """
    TC-SYS-003-004: Downstream Traceability (API)

    @links: SYS-003
    @test_id: TC-SYS-003-004

    Verify system can trace downstream from requirements to tests.
    """
    # Initialize core with test DHF
    core = CompliantFlowCore(test_dhf_root)
    graph = core.graph

    # Find descendants of SYS-001 (should include SRS items)
    descendants = graph.find_descendants("SYS-001")

    # Should have some descendants
    assert len(descendants) > 0, "SYS-001 should have downstream items"

    # Descendants should include derived SRS items
    descendant_ids = [d.id for d in descendants]

    # Check that we can trace down the hierarchy
    srs_item = core.get_item("SRS-001")
    if srs_item.derives_from and "SYS-001" in srs_item.derives_from:
        assert "SRS-001" in descendant_ids, "SRS-001 should be descendant of SYS-001"


def test_TC_SYS_003_005_upstream_traceability(test_dhf_root):
    """
    TC-SYS-003-005: Upstream Traceability (API)

    @links: SYS-003
    @test_id: TC-SYS-003-005

    Verify system can trace upstream from tests to requirements.
    """
    # Initialize core with test DHF
    core = CompliantFlowCore(test_dhf_root)
    graph = core.graph

    # Find ancestors of SRS-001 (should include SYS, CRS, UC)
    ancestors = graph.find_ancestors("SRS-001")

    # Should have some ancestors
    assert len(ancestors) > 0, "SRS-001 should have upstream items"

    # Get ancestor IDs
    ancestor_ids = [a.id for a in ancestors]

    # Should be able to trace back to SYS items
    srs_item = core.get_item("SRS-001")
    if srs_item.derives_from:
        # At least one parent should be in ancestors
        assert any(parent_id in ancestor_ids for parent_id in srs_item.derives_from), \
            "Direct parents should be in ancestors"
