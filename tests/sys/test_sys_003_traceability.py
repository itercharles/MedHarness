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

from utils.local_adapter import LocalDHFAdapter
from compliantflow.core import CompliantFlowCore


def test_TC_SYS_003_001_traceability_matrix_data(test_dhf_root):
    """
    TC-SYS-003-001: Traceability Matrix Data (API)

    @links: SYS-003
    @test_id: TC-SYS-003-001

    Verify system can generate traceability matrix data.
    """
    # Initialize core with test DHF
    core = CompliantFlowCore(LocalDHFAdapter(test_dhf_root))

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
    core = CompliantFlowCore(LocalDHFAdapter(test_dhf_root))

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
    core = CompliantFlowCore(LocalDHFAdapter(test_dhf_root))

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
    core = CompliantFlowCore(LocalDHFAdapter(test_dhf_root))
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
    core = CompliantFlowCore(LocalDHFAdapter(test_dhf_root))
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


def test_build_traceability_chains_structure(test_dhf_root):
    """
    TC-SYS-003-008: build_traceability_chains API (API)

    @links: SYS-003
    @test_id: TC-SYS-003-008

    Verify core.build_traceability_chains() returns structured chain data.
    """
    core = CompliantFlowCore(LocalDHFAdapter(test_dhf_root))

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
    core = CompliantFlowCore(LocalDHFAdapter(test_dhf_root))

    chains = core.build_traceability_chains(["CRS", "SYS", "SRS"])

    complete_chains = [c for c in chains if c["is_complete"]]
    assert len(complete_chains) > 0, "Should have at least one complete chain"

    # A complete chain should have non-None items at every level
    for chain in complete_chains:
        for code in ["CRS", "SYS", "SRS"]:
            assert chain[code] is not None, f"Complete chain must have item at '{code}'"
            assert "id" in chain[code]


def test_get_vertical_view_items_focus_only(test_dhf_root):
    """
    TC-SYS-003-010: get_vertical_view_items returns focus items (API)

    @links: SYS-003
    @test_id: TC-SYS-003-010

    Verify get_vertical_view_items includes the focus type items when both
    show_upstream and show_downstream are False.
    """
    core = CompliantFlowCore(LocalDHFAdapter(test_dhf_root))

    result = core.get_vertical_view_items("SYS", show_upstream=False, show_downstream=False)

    assert len(result) > 0, "Should return at least the focus items"
    for item_id in result:
        assert core.get_doc_type_code(item_id) == "SYS", "All returned items should be SYS type"


def test_get_vertical_view_items_with_upstream(test_dhf_root):
    """
    TC-SYS-003-011: get_vertical_view_items includes upstream items (API)

    @links: SYS-003
    @test_id: TC-SYS-003-011

    Verify get_vertical_view_items includes items that link TO the focus type
    when show_upstream=True.
    """
    core = CompliantFlowCore(LocalDHFAdapter(test_dhf_root))

    focus_only = core.get_vertical_view_items("SYS", show_upstream=False, show_downstream=False)
    with_upstream = core.get_vertical_view_items("SYS", show_upstream=True, show_downstream=False)

    # Upstream should add more items (SRS items link to SYS)
    assert len(with_upstream) >= len(focus_only), "Upstream view should have at least as many items"
    # SRS-001 derives from SYS-001, so it links to SYS → should appear as upstream
    assert "SRS-001" in with_upstream, "SRS-001 should appear as upstream of SYS focus"


def test_get_vertical_view_items_with_downstream(test_dhf_root):
    """
    TC-SYS-003-012: get_vertical_view_items includes downstream items (API)

    @links: SYS-003
    @test_id: TC-SYS-003-012

    Verify get_vertical_view_items includes items that the focus items link TO
    when show_downstream=True.
    """
    core = CompliantFlowCore(LocalDHFAdapter(test_dhf_root))

    focus_only = core.get_vertical_view_items("SYS", show_upstream=False, show_downstream=False)
    with_downstream = core.get_vertical_view_items("SYS", show_upstream=False, show_downstream=True)

    # Downstream should add more items (SYS items link to CRS)
    assert len(with_downstream) >= len(focus_only), "Downstream view should have at least as many items"
    # SYS-001 derives from CRS-001, so CRS-001 is downstream
    assert "CRS-001" in with_downstream, "CRS-001 should appear as downstream of SYS focus"


def test_get_vertical_view_items_unknown_type(test_dhf_root):
    """
    TC-SYS-003-013: get_vertical_view_items returns empty for unknown type (API)

    @links: SYS-003
    @test_id: TC-SYS-003-013
    """
    core = CompliantFlowCore(LocalDHFAdapter(test_dhf_root))

    result = core.get_vertical_view_items("NONEXISTENT")

    assert result == {}, "Should return empty dict for unknown focus type"


def test_get_doc_type_code(test_dhf_root):
    """
    TC-SYS-003-014: get_doc_type_code resolves item ID to doc type (API)

    @links: SYS-003
    @test_id: TC-SYS-003-014
    """
    core = CompliantFlowCore(LocalDHFAdapter(test_dhf_root))

    assert core.get_doc_type_code("SRS-001") == "SRS"
    assert core.get_doc_type_code("SYS-002") == "SYS"
    assert core.get_doc_type_code("CRS-001") == "CRS"
    assert core.get_doc_type_code("UNKNOWN-999") == "OTHER"


# ---------------------------------------------------------------------------
# build_traceability_matrix
# ---------------------------------------------------------------------------

def test_build_traceability_matrix_structure(test_dhf_root):
    """
    TC-SYS-003-015: build_traceability_matrix returns columns + rows (API)

    @links: SYS-003
    @test_id: TC-SYS-003-015

    Verify the return dict has 'columns' and 'rows' keys, and each row
    contains exactly the requested doc-type keys plus meta keys.
    """
    core = CompliantFlowCore(LocalDHFAdapter(test_dhf_root))
    result = core.build_traceability_matrix(["CRS", "SYS", "SRS"])

    assert "columns" in result
    assert "rows" in result
    assert result["columns"] == ["CRS", "SYS", "SRS"]

    meta_keys = {"is_orphan", "orphan_type", "is_complete"}
    for row in result["rows"]:
        assert set(row.keys()) == {"CRS", "SYS", "SRS"} | meta_keys
        # cell values are item IDs (str) or None — never dicts
        for dt in ["CRS", "SYS", "SRS"]:
            assert row[dt] is None or isinstance(row[dt], str)


def test_build_traceability_matrix_linked_items(test_dhf_root):
    """
    TC-SYS-003-016: build_traceability_matrix rows contain correct IDs (API)

    @links: SYS-003
    @test_id: TC-SYS-003-016

    CRS-001 → SYS-001 → SRS-001 and SRS-002 must appear as complete rows.
    """
    core = CompliantFlowCore(LocalDHFAdapter(test_dhf_root))
    result = core.build_traceability_matrix(["CRS", "SYS", "SRS"])

    complete_rows = [r for r in result["rows"] if r["is_complete"]]
    assert len(complete_rows) >= 1

    # Both SRS items that derive from SYS-001 should produce complete rows
    srs_ids_in_complete = {r["SRS"] for r in complete_rows}
    assert "SRS-001" in srs_ids_in_complete
    assert "SRS-002" in srs_ids_in_complete


def test_build_traceability_matrix_orphans_included(test_dhf_root):
    """
    TC-SYS-003-017: build_traceability_matrix includes orphan rows (API)

    @links: SYS-003
    @test_id: TC-SYS-003-017

    SYS-002 derives from CRS-001 but has no SRS children — it must appear
    as an orphan row (is_complete=False) with SRS=None.
    """
    core = CompliantFlowCore(LocalDHFAdapter(test_dhf_root))
    result = core.build_traceability_matrix(["CRS", "SYS", "SRS"])

    sys2_rows = [r for r in result["rows"] if r["SYS"] == "SYS-002"]
    assert sys2_rows, "SYS-002 must appear in the matrix"
    assert all(r["SRS"] is None for r in sys2_rows)
    assert all(not r["is_complete"] for r in sys2_rows)


def test_build_traceability_matrix_custom_path(test_dhf_root):
    """
    TC-SYS-003-018: build_traceability_matrix accepts any doc-type subset (API)

    @links: SYS-003
    @test_id: TC-SYS-003-018
    """
    core = CompliantFlowCore(LocalDHFAdapter(test_dhf_root))
    # Two-column matrix
    result = core.build_traceability_matrix(["SYS", "SRS"])
    assert result["columns"] == ["SYS", "SRS"]
    assert len(result["rows"]) > 0


# ---------------------------------------------------------------------------
# get_item_chain
# ---------------------------------------------------------------------------

def test_get_item_chain_unknown_item(test_dhf_root):
    """
    TC-SYS-003-019: get_item_chain returns None for unknown item (API)

    @links: SYS-003
    @test_id: TC-SYS-003-019
    """
    core = CompliantFlowCore(LocalDHFAdapter(test_dhf_root))
    assert core.get_item_chain("DOES-NOT-EXIST") is None


def test_get_item_chain_structure(test_dhf_root):
    """
    TC-SYS-003-020: get_item_chain returns root + nodes dict (API)

    @links: SYS-003
    @test_id: TC-SYS-003-020

    Verify the top-level shape and that each node has the expected keys.
    """
    core = CompliantFlowCore(LocalDHFAdapter(test_dhf_root))
    result = core.get_item_chain("SYS-001")

    assert result is not None
    assert result["root"] == "SYS-001"
    assert "nodes" in result
    assert isinstance(result["nodes"], dict)

    node_keys = {"id", "title", "status", "type", "upstream", "downstream"}
    for node in result["nodes"].values():
        assert node_keys <= set(node.keys())
        assert isinstance(node["upstream"], list)
        assert isinstance(node["downstream"], list)


def test_get_item_chain_transitive_coverage(test_dhf_root):
    """
    TC-SYS-003-021: get_item_chain includes all transitively connected items (API)

    @links: SYS-003
    @test_id: TC-SYS-003-021

    Starting from SYS-001:
      upstream:   CRS-001 → UC-001
      downstream: SRS-001, SRS-002, SYSARCH-001
    All must appear in nodes.
    """
    core = CompliantFlowCore(LocalDHFAdapter(test_dhf_root))
    result = core.get_item_chain("SYS-001")
    node_ids = set(result["nodes"].keys())

    assert "SYS-001"    in node_ids
    assert "CRS-001"    in node_ids  # direct upstream
    assert "UC-001"     in node_ids  # transitive upstream
    assert "SRS-001"    in node_ids  # direct downstream
    assert "SRS-002"    in node_ids  # direct downstream
    assert "SYSARCH-001" in node_ids  # downstream (implements SYS-001)


def test_get_item_chain_direct_neighbours_only(test_dhf_root):
    """
    TC-SYS-003-022: get_item_chain upstream/downstream lists are direct only (API)

    @links: SYS-003
    @test_id: TC-SYS-003-022

    SYS-001's upstream must be [CRS-001] (direct parent), NOT UC-001
    (which is the grandparent — reachable via nodes dict, not listed directly).
    """
    core = CompliantFlowCore(LocalDHFAdapter(test_dhf_root))
    result = core.get_item_chain("SYS-001")
    sys_node = result["nodes"]["SYS-001"]

    assert "CRS-001" in sys_node["upstream"]
    assert "UC-001"  not in sys_node["upstream"]   # transitive, not direct

    assert "SRS-001"    in sys_node["downstream"]
    assert "SRS-002"    in sys_node["downstream"]
    assert "SYSARCH-001" in sys_node["downstream"]


def test_get_item_chain_leaf_item(test_dhf_root):
    """
    TC-SYS-003-023: get_item_chain works for a leaf item with no downstream (API)

    @links: SYS-003
    @test_id: TC-SYS-003-023
    """
    core = CompliantFlowCore(LocalDHFAdapter(test_dhf_root))
    result = core.get_item_chain("UC-001")

    assert result is not None
    assert result["root"] == "UC-001"
    uc_node = result["nodes"]["UC-001"]
    assert uc_node["upstream"] == []        # UC has no parents
    assert len(uc_node["downstream"]) > 0   # CRS-001 derives from UC-001
