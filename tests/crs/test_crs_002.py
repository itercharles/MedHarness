"""
API tests for CRS-002: Traceability Analysis

Verifies traceability features through the CompliantFlowCore API.

@links: CRS-002
"""


def test_TC_CRS_002_003_navigate_parent_links(core):
    """
    TC-CRS-002-003: Navigate Parent Links via API

    @test_id: TC-CRS-002-003
    @links: CRS-002

    get_item_chain() for SRS-001 includes SYS-001 as a direct upstream neighbour,
    reflecting the derives_from relationship defined in the test fixture.
    """
    chain = core.get_item_chain("SRS-001")
    node = chain["nodes"]["SRS-001"]

    assert "upstream" in node, "Expected 'upstream' key in chain node"
    assert "downstream" in node, "Expected 'downstream' key in chain node"
    assert isinstance(node["upstream"], list)
    assert "SYS-001" in node["upstream"], \
        f"Expected SYS-001 in upstream of SRS-001, got: {node['upstream']}"
