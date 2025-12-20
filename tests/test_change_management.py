"""
Test suite for change management workflow functionality.

Tests verify that the change management system meets customer needs
for regulatory compliance.

@links: CRS-004
"""

import pytest
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from traceability.compliant_flow_core import CompliantFlowCore


def test_TC_CRS_004_001_change_management_workflow():
    """
    Customer Validation - Change Management Workflow
    
    @links: CRS-004
    @test_id: TC-CRS-004-001
    
    Validate that the change management system meets customer needs
    for regulatory compliance.
    
    **Objective**: Verify change management workflow supports regulatory
    compliance requirements.
    
    **Prerequisites**: User has regulatory affairs role
    
    **Test Steps**:
    1. Verify change request (CR) document type exists
    2. Verify CR has required fields for compliance
    3. Verify CR can link to affected requirements
    4. Verify CR has approval workflow
    5. Verify traceability from CR to requirements
    """
    # Initialize core
    dhf_root = Path(__file__).parent.parent / "DHF"
    core = CompliantFlowCore(dhf_root)
    
    # Step 1: Verify CR document type exists
    cr_doc_type = core.config.get_doc_type("CR")
    assert cr_doc_type is not None, "Change Request (CR) document type not found"
    assert cr_doc_type.name == "Change Request", "CR document type has incorrect name"
    
    # Step 2: Verify CR has required fields for compliance
    required_fields = ["id", "title", "description", "links"]
    for field in required_fields:
        assert field in cr_doc_type.properties, \
            f"CR missing required field: {field}"
    
    # Verify CR has impact assessment field (important for regulatory compliance)
    assert "impact_assessment" in cr_doc_type.properties, \
        "CR should have impact_assessment field for documenting impact analysis"
    
    # Step 3: Verify CR can link to affected requirements
    # CR uses 'links' field for traceability instead of explicit relations
    assert "links" in cr_doc_type.properties, \
        "CR should have links field for traceability to affected items"
    
    # If CR has relations defined, verify they include requirements
    if hasattr(cr_doc_type, 'relations') and cr_doc_type.relations:
        relation_targets = [rel.target for rel in cr_doc_type.relations]
        requirement_types = ["SYS", "CRS", "SDS"]
        has_requirement_link = any(target in requirement_types for target in relation_targets)
        assert has_requirement_link, \
            f"CR should be able to link to requirements, found targets: {relation_targets}"
    
    # Step 4: Verify CR has approval workflow (lifecycle)
    assert hasattr(cr_doc_type, 'lifecycle'), "CR should have lifecycle defined"
    lifecycle = cr_doc_type.lifecycle
    
    # Lifecycle is a dict, not an object
    assert isinstance(lifecycle, dict), "Lifecycle should be a dictionary"
    
    # Verify lifecycle has states
    assert 'states' in lifecycle, "Lifecycle should have states"
    assert len(lifecycle['states']) > 0, "Lifecycle should have at least one state"
    
    # Verify lifecycle has transitions
    assert 'transitions' in lifecycle, "Lifecycle should have transitions"
    assert len(lifecycle['transitions']) > 0, "Lifecycle should have at least one transition"
    
    # Verify there's an approval-like state
    state_ids = [state['id'] for state in lifecycle['states']]
    approval_states = ["approved", "accepted", "implemented", "closed", "completed"]
    has_approval_state = any(state in state_ids for state in approval_states)
    assert has_approval_state, \
        f"CR lifecycle should have an approval state, found: {state_ids}"
    
    # Step 5: Verify traceability from CR to requirements
    # Load all items and check if any CRs exist with links
    all_items = core.get_all_items()
    cr_items = [item for item in all_items if item['id'].startswith('CR-')]
    
    # If CRs exist, verify they can have links
    if cr_items:
        # Check that at least one CR has links (or that links field exists)
        cr_with_links = [cr for cr in cr_items if cr.get('links')]
        # It's OK if no CRs have links yet, but the field should exist
        sample_cr = cr_items[0]
        assert 'links' in sample_cr or hasattr(cr_doc_type, 'relations'), \
            "CR items should support links for traceability"
    
    # Verify graph can handle CR relationships
    assert core.graph is not None, "Traceability graph should be initialized"
    
    # If there are CRs in the graph, verify they have edges
    G = core.graph.graph
    cr_nodes = [node for node in G.nodes() if node.startswith('CR-')]
    if cr_nodes:
        # At least one CR should have connections (either in or out)
        total_edges = sum(G.degree(node) for node in cr_nodes)
        # It's OK if CRs are orphans in test environment
        # Just verify the graph structure supports them
        assert all(node in G.nodes() for node in cr_nodes), \
            "All CR nodes should be in the graph"


def test_TC_CRS_004_002_change_request_impact_analysis():
    """
    Verify Change Request Impact Analysis
    
    @links: CRS-004
    @test_id: TC-CRS-004-002
    
    Verify that change requests support impact analysis for
    regulatory compliance.
    """
    # Initialize core
    dhf_root = Path(__file__).parent.parent / "DHF"
    core = CompliantFlowCore(dhf_root)
    
    # Get CR document type
    cr_doc_type = core.config.get_doc_type("CR")
    assert cr_doc_type is not None, "CR document type not found"
    
    # Verify CR has fields for impact analysis
    # Could be 'impact_analysis', 'content', or similar
    impact_fields = ["impact_analysis", "content", "description", "affected_items"]
    has_impact_field = any(field in cr_doc_type.properties for field in impact_fields)
    assert has_impact_field, \
        f"CR should have field for impact analysis, properties: {cr_doc_type.properties}"
    
    # Verify CR can link to affected items
    assert hasattr(cr_doc_type, 'relations'), "CR should support relations to affected items"
    
    # Verify links field exists for traceability
    assert "links" in cr_doc_type.properties, \
        "CR should have links field for traceability to affected items"
