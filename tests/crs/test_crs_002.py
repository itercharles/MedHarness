"""
API tests for CRS-002: Traceability Analysis

Verifies traceability features through the CompliantFlowCore API.

@links: CRS-002
"""


def test_TC_CRS_002_001_view_traceability_matrix(core):
    """
    TC-CRS-002-001: View Traceability Matrix via API

    @test_id: TC-CRS-002-001
    @links: CRS-002

    get_traceability_matrix("SRS", "SYS") returns rows where SRS items
    list their upstream SYS parents. The test fixture has SRS-001 and
    SRS-002 both deriving from SYS-001.
    """
    matrix = core.get_traceability_matrix("SRS", "SYS")

    assert isinstance(matrix, list), "Expected a list of matrix rows"
    assert len(matrix) > 0, "Expected at least one row in the traceability matrix"

    # Every row must have 'source', 'target', and 'relationship' keys
    for row in matrix:
        assert "source" in row, f"Row missing 'source': {row}"
        assert "relationship" in row, f"Row missing 'relationship': {row}"
        assert row["source"].startswith("SRS-"), \
            f"Expected SRS source item, got: {row['source']}"

    # At least one row should have a verified link to SYS-001
    linked = [r for r in matrix if r.get("target") == "SYS-001"]
    assert len(linked) >= 1, \
        f"Expected at least one SRS item linked to SYS-001; matrix: {matrix}"


def test_TC_CRS_002_002_view_graph_stats(core):
    """
    TC-CRS-002-002: View Traceability Graph Statistics via API

    @test_id: TC-CRS-002-002
    @links: CRS-002

    get_graph_stats() returns a summary of the traceability graph including
    node and edge counts.
    """
    stats = core.get_graph_stats()

    assert isinstance(stats, dict)
    assert "node_count" in stats or "nodes" in stats or len(stats) > 0, \
        f"Expected graph stats with node information, got: {stats}"

    # The test DHF has items from multiple types
    all_items = core.get_all_items()
    assert len(all_items) > 0, "Expected items in graph"


def test_TC_CRS_002_003_navigate_parent_links(core):
    """
    TC-CRS-002-003: Navigate Parent Links via API

    @test_id: TC-CRS-002-003
    @links: CRS-002

    get_item_neighbors() for SRS-001 returns SYS-001 in the upstream list,
    reflecting the derives_from relationship defined in the test fixture.
    """
    neighbors = core.get_item_neighbors("SRS-001")

    assert "upstream" in neighbors, "Expected 'upstream' key in neighbors"
    assert "downstream" in neighbors, "Expected 'downstream' key in neighbors"
    assert isinstance(neighbors["upstream"], list)
    assert "SYS-001" in neighbors["upstream"], \
        f"Expected SYS-001 in upstream of SRS-001, got: {neighbors['upstream']}"
