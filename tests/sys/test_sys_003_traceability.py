"""
API tests for SYS-003: Visual Traceability

Verifies: The system shall provide visual traceability between requirements,
design items, and test cases.

@links: SYS-003
"""

import pytest

from compliantflow.core import CompliantFlowCore


def test_TC_SYS_003_001_traceability_matrix_data(stub_adapter):
    """
    TC-SYS-003-001: Traceability Matrix Data (API)

    @links: SYS-003
    @test_id: TC-SYS-003-001

    Verify system can generate traceability matrix data.
    """
    core = CompliantFlowCore(stub_adapter)

    all_items = core.get_all_items()

    item_types = set(item["id"].split("-")[0] for item in all_items)

    assert "UC" in item_types, "Should have Use Case items"
    assert "CRS" in item_types, "Should have Customer Requirement items"
    assert "SYS" in item_types, "Should have System Requirement items"
    assert "SRS" in item_types, "Should have Software Requirement items"

    item_ids = [item["id"] for item in all_items]
    assert "UC-001" in item_ids
    assert "CRS-001" in item_ids
    assert "SYS-001" in item_ids
    assert "SRS-001" in item_ids


def test_TC_SYS_003_002_traceability_graph(stub_adapter):
    """
    TC-SYS-003-002: Traceability Graph (API)

    @links: SYS-003
    @test_id: TC-SYS-003-002

    Verify system can build a traceability graph.
    """
    core = CompliantFlowCore(stub_adapter)

    graph = core.graph

    assert graph.graph.number_of_nodes() > 0, "Graph should have nodes"
    assert graph.graph.number_of_edges() > 0, "Graph should have edges (relationships)"

    assert graph.graph.has_node("UC-001")
    assert graph.graph.has_node("CRS-001")
    assert graph.graph.has_node("SYS-001")
    assert graph.graph.has_node("SRS-001")


def test_TC_SYS_003_003_traceability_relationships(stub_adapter):
    """
    TC-SYS-003-003: Traceability Relationships (API)

    @links: SYS-003
    @test_id: TC-SYS-003-003

    Verify system correctly tracks relationships between items.
    """
    core = CompliantFlowCore(stub_adapter)

    srs_item = core.get_item("SRS-001")

    assert "derives_from" in srs_item
    assert srs_item["derives_from"] is not None
    assert len(srs_item["derives_from"]) > 0

    sys_item = core.get_item("SYS-001")
    assert "derives_from" in sys_item
    assert sys_item["derives_from"] is not None


def test_TC_SYS_003_004_downstream_traceability(stub_adapter):
    """
    TC-SYS-003-004: Downstream Traceability (API)

    @links: SYS-003
    @test_id: TC-SYS-003-004

    Verify system can trace downstream from requirements to tests.
    """
    core = CompliantFlowCore(stub_adapter)
    graph = core.graph

    downstream_uids = graph.get_downstream("SYS-001")

    assert len(downstream_uids) > 0, "SYS-001 should have downstream items"

    srs_item = core.get_item("SRS-001")
    if srs_item.get("derives_from") and "SYS-001" in srs_item["derives_from"]:
        assert "SRS-001" in downstream_uids, "SRS-001 should be downstream of SYS-001"


def test_TC_SYS_003_005_upstream_traceability(stub_adapter):
    """
    TC-SYS-003-005: Upstream Traceability (API)

    @links: SYS-003
    @test_id: TC-SYS-003-005

    Verify system can trace upstream from tests to requirements.
    """
    core = CompliantFlowCore(stub_adapter)
    graph = core.graph

    upstream_uids = graph.get_upstream("SRS-001")

    assert len(upstream_uids) > 0, "SRS-001 should have upstream items"

    srs_item = core.get_item("SRS-001")
    if srs_item.get("derives_from"):
        assert any(parent_id in upstream_uids for parent_id in srs_item["derives_from"]), \
            "Direct parents should be in upstream"


def test_build_traceability_chains_structure(stub_adapter):
    """
    TC-SYS-003-008: build_traceability_chains API (API)

    @links: SYS-003
    @test_id: TC-SYS-003-008

    Verify core.build_traceability_chains() returns structured chain data.
    """
    core = CompliantFlowCore(stub_adapter)

    chains = core.build_traceability_chains(["CRS", "SYS", "SRS"])

    assert isinstance(chains, list)
    assert len(chains) > 0, "Should produce at least one chain"

    for chain in chains:
        assert "is_orphan" in chain
        assert "is_complete" in chain
        assert isinstance(chain["is_orphan"], bool)
        assert isinstance(chain["is_complete"], bool)
        for code in ["CRS", "SYS", "SRS"]:
            assert code in chain, f"Chain should have key '{code}'"


def test_build_traceability_chains_complete_chain(stub_adapter):
    """
    TC-SYS-003-009: build_traceability_chains complete chain (API)

    @links: SYS-003
    @test_id: TC-SYS-003-009

    Verify a complete chain exists when all links are present.
    """
    core = CompliantFlowCore(stub_adapter)

    chains = core.build_traceability_chains(["CRS", "SYS", "SRS"])

    complete_chains = [c for c in chains if c["is_complete"]]
    assert len(complete_chains) > 0, "Should have at least one complete chain"

    for chain in complete_chains:
        for code in ["CRS", "SYS", "SRS"]:
            assert chain[code] is not None, f"Complete chain must have item at '{code}'"
            assert "id" in chain[code]


def test_build_traceability_matrix_structure(stub_adapter):
    """
    TC-SYS-003-015: build_traceability_matrix returns columns + rows (API)

    @links: SYS-003
    @test_id: TC-SYS-003-015

    Verify the return dict has 'columns' and 'rows' keys, and each row
    contains exactly the requested doc-type keys plus meta keys.
    """
    core = CompliantFlowCore(stub_adapter)
    result = core.build_traceability_matrix(["CRS", "SYS", "SRS"])

    assert "columns" in result
    assert "rows" in result
    assert result["columns"] == ["CRS", "SYS", "SRS"]

    meta_keys = {"is_orphan", "orphan_type", "is_complete"}
    for row in result["rows"]:
        assert set(row.keys()) == {"CRS", "SYS", "SRS"} | meta_keys
        for dt in ["CRS", "SYS", "SRS"]:
            assert row[dt] is None or isinstance(row[dt], str)


def test_build_traceability_matrix_linked_items(stub_adapter):
    """
    TC-SYS-003-016: build_traceability_matrix rows contain correct IDs (API)

    @links: SYS-003
    @test_id: TC-SYS-003-016

    CRS-001 → SYS-001 → SRS-001 and SRS-002 must appear as complete rows.
    """
    core = CompliantFlowCore(stub_adapter)
    result = core.build_traceability_matrix(["CRS", "SYS", "SRS"])

    complete_rows = [r for r in result["rows"] if r["is_complete"]]
    assert len(complete_rows) >= 1

    srs_ids_in_complete = {r["SRS"] for r in complete_rows}
    assert "SRS-001" in srs_ids_in_complete
    assert "SRS-002" in srs_ids_in_complete


def test_build_traceability_matrix_orphans_included(stub_adapter):
    """
    TC-SYS-003-017: build_traceability_matrix includes orphan rows (API)

    @links: SYS-003
    @test_id: TC-SYS-003-017

    SYS-002 derives from CRS-001 but has no SRS children — it must appear
    as an orphan row (is_complete=False) with SRS=None.
    """
    core = CompliantFlowCore(stub_adapter)
    result = core.build_traceability_matrix(["CRS", "SYS", "SRS"])

    sys2_rows = [r for r in result["rows"] if r["SYS"] == "SYS-002"]
    assert sys2_rows, "SYS-002 must appear in the matrix"
    assert all(r["SRS"] is None for r in sys2_rows)
    assert all(not r["is_complete"] for r in sys2_rows)


def test_build_traceability_matrix_custom_path(stub_adapter):
    """
    TC-SYS-003-018: build_traceability_matrix accepts any doc-type subset (API)

    @links: SYS-003
    @test_id: TC-SYS-003-018
    """
    core = CompliantFlowCore(stub_adapter)
    result = core.build_traceability_matrix(["SYS", "SRS"])
    assert result["columns"] == ["SYS", "SRS"]
    assert len(result["rows"]) > 0


def test_get_item_chain_unknown_item(stub_adapter):
    """
    TC-SYS-003-019: get_item_chain returns None for unknown item (API)

    @links: SYS-003
    @test_id: TC-SYS-003-019
    """
    core = CompliantFlowCore(stub_adapter)
    assert core.get_item_chain("DOES-NOT-EXIST") is None


def test_get_item_chain_structure(stub_adapter):
    """
    TC-SYS-003-020: get_item_chain returns root + nodes dict (API)

    @links: SYS-003
    @test_id: TC-SYS-003-020

    Verify the top-level shape and that each node has the expected keys.
    """
    core = CompliantFlowCore(stub_adapter)
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


def test_get_item_chain_transitive_coverage(stub_adapter):
    """
    TC-SYS-003-021: get_item_chain includes all transitively connected items (API)

    @links: SYS-003
    @test_id: TC-SYS-003-021

    Starting from SYS-001:
      upstream:   CRS-001 → UC-001
      downstream: SRS-001, SRS-002, SYSARCH-001
    All must appear in nodes.
    """
    core = CompliantFlowCore(stub_adapter)
    result = core.get_item_chain("SYS-001")
    node_ids = set(result["nodes"].keys())

    assert "SYS-001"    in node_ids
    assert "CRS-001"    in node_ids
    assert "UC-001"     in node_ids
    assert "SRS-001"    in node_ids
    assert "SRS-002"    in node_ids
    assert "SYSARCH-001" in node_ids


def test_get_item_chain_direct_neighbours_only(stub_adapter):
    """
    TC-SYS-003-022: get_item_chain upstream/downstream lists are direct only (API)

    @links: SYS-003
    @test_id: TC-SYS-003-022

    SYS-001's upstream must be [CRS-001] (direct parent), NOT UC-001
    (which is the grandparent — reachable via nodes dict, not listed directly).
    """
    core = CompliantFlowCore(stub_adapter)
    result = core.get_item_chain("SYS-001")
    sys_node = result["nodes"]["SYS-001"]

    assert "CRS-001" in sys_node["upstream"]
    assert "UC-001"  not in sys_node["upstream"]

    assert "SRS-001"    in sys_node["downstream"]
    assert "SRS-002"    in sys_node["downstream"]
    assert "SYSARCH-001" in sys_node["downstream"]


def test_get_item_chain_leaf_item(stub_adapter):
    """
    TC-SYS-003-023: get_item_chain works for a leaf item with no downstream (API)

    @links: SYS-003
    @test_id: TC-SYS-003-023
    """
    core = CompliantFlowCore(stub_adapter)
    result = core.get_item_chain("UC-001")

    assert result is not None
    assert result["root"] == "UC-001"
    uc_node = result["nodes"]["UC-001"]
    assert uc_node["upstream"] == []
    assert len(uc_node["downstream"]) > 0
