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
    item_types = set(item["id"].split("-")[0] for item in all_items)

    assert "UC" in item_types, "Should have Use Case items"
    assert "CRS" in item_types, "Should have Customer Requirement items"
    assert "SYS" in item_types, "Should have System Requirement items"
    assert "SRS" in item_types, "Should have Software Requirement items"

    # Verify specific test items exist
    item_ids = [item["id"] for item in all_items]
    assert "UC-001" in item_ids
    assert "CRS-001" in item_ids
    assert "SYS-001" in item_ids
    assert "SRS-001" in item_ids


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
    assert "derives_from" in srs_item
    assert srs_item["derives_from"] is not None
    assert len(srs_item["derives_from"]) > 0

    # Get SYS-001 and verify it derives from CRS
    sys_item = core.get_item("SYS-001")
    assert "derives_from" in sys_item
    assert sys_item["derives_from"] is not None


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

    # Get downstream items from SYS-001 (returns set of UIDs)
    downstream_uids = graph.get_downstream("SYS-001")

    # Should have some downstream items
    assert len(downstream_uids) > 0, "SYS-001 should have downstream items"

    # Check that we can trace down the hierarchy
    srs_item = core.get_item("SRS-001")
    if srs_item.get("derives_from") and "SYS-001" in srs_item["derives_from"]:
        assert "SRS-001" in downstream_uids, "SRS-001 should be downstream of SYS-001"


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

    # Get upstream items from SRS-001 (returns set of UIDs)
    upstream_uids = graph.get_upstream("SRS-001")

    # Should have some upstream items
    assert len(upstream_uids) > 0, "SRS-001 should have upstream items"

    # Should be able to trace back to SYS items
    srs_item = core.get_item("SRS-001")
    if srs_item.get("derives_from"):
        # At least one parent should be in upstream
        assert any(parent_id in upstream_uids for parent_id in srs_item["derives_from"]), \
            "Direct parents should be in upstream"


def test_get_item_neighbors_returns_upstream_and_downstream(test_dhf_root):
    """
    TC-SYS-003-006: get_item_neighbors API (API)

    @links: SYS-003
    @test_id: TC-SYS-003-006

    Verify core.get_item_neighbors() returns correct upstream/downstream lists.
    """
    core = CompliantFlowCore(test_dhf_root)

    neighbors = core.get_item_neighbors("SYS-001")

    assert "upstream" in neighbors
    assert "downstream" in neighbors
    assert isinstance(neighbors["upstream"], list)
    assert isinstance(neighbors["downstream"], list)

    # SYS-001 derives_from CRS-001 → CRS-001 should be upstream
    assert "CRS-001" in neighbors["upstream"], "CRS-001 should be upstream of SYS-001"
    # SRS-001 derives_from SYS-001 → SRS-001 should be downstream
    assert "SRS-001" in neighbors["downstream"], "SRS-001 should be downstream of SYS-001"


def test_get_item_neighbors_unknown_item(test_dhf_root):
    """
    TC-SYS-003-007: get_item_neighbors with unknown item (API)

    @links: SYS-003
    @test_id: TC-SYS-003-007

    Verify get_item_neighbors returns empty lists for unknown items.
    """
    core = CompliantFlowCore(test_dhf_root)

    neighbors = core.get_item_neighbors("NONEXISTENT-999")

    assert neighbors["upstream"] == []
    assert neighbors["downstream"] == []


def test_build_traceability_chains_structure(test_dhf_root):
    """
    TC-SYS-003-008: build_traceability_chains API (API)

    @links: SYS-003
    @test_id: TC-SYS-003-008

    Verify core.build_traceability_chains() returns structured chain data.
    """
    core = CompliantFlowCore(test_dhf_root)

    chains = core.build_traceability_chains(["CRS", "SYS", "SRS"])

    assert isinstance(chains, list)
    assert len(chains) > 0, "Should produce at least one chain"

    for chain in chains:
        assert "is_orphan" in chain
        assert "is_complete" in chain
        assert isinstance(chain["is_orphan"], bool)
        assert isinstance(chain["is_complete"], bool)
        # Each path level should be a key
        for code in ["CRS", "SYS", "SRS"]:
            assert code in chain, f"Chain should have key '{code}'"


def test_build_traceability_chains_complete_chain(test_dhf_root):
    """
    TC-SYS-003-009: build_traceability_chains complete chain (API)

    @links: SYS-003
    @test_id: TC-SYS-003-009

    Verify a complete chain exists when all links are present.
    """
    core = CompliantFlowCore(test_dhf_root)

    chains = core.build_traceability_chains(["CRS", "SYS", "SRS"])

    complete_chains = [c for c in chains if c["is_complete"]]
    assert len(complete_chains) > 0, "Should have at least one complete chain"

    # A complete chain should have non-None items at every level
    for chain in complete_chains:
        for code in ["CRS", "SYS", "SRS"]:
            assert chain[code] is not None, f"Complete chain must have item at '{code}'"
            assert "id" in chain[code]
