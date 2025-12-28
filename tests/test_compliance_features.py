"""
Test suite for Compliance Features (SOUP, Defect, Release, etc.).

These tests verify that the compliance requirements are correctly implemented
in the CompliantFlow system.
"""

import pytest
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from traceability.compliant_flow_core import CompliantFlowCore


def test_TC_SOUP_001_001_soup_document_type_configuration():
    """
    Verify SOUP Document Type Configuration
    
    @test_id: TC-SOUP-001-001
    
    Verify that SOUP document type is configured with all required properties
    and lifecycle states per IEC 62304 requirements.
    """
    # Initialize core
    dhf_root = Path(__file__).parent.parent / "DHF"
    core = CompliantFlowCore(dhf_root)
    
    # Verify SOUP document type exists
    soup_doc_type = core.config.get_doc_type("SOUP")
    assert soup_doc_type is not None, "SOUP document type not found in configuration"
    # SOUP name is "Software of Unknown Provenance"
    assert "SOUP" in soup_doc_type.code or "Software of Unknown Provenance" in soup_doc_type.name, \
        "SOUP document type has incorrect name"
    
    # Verify required properties
    required_props = ["id", "title", "content", "name", "version", "safety_class", "purpose"]
    for prop in required_props:
        assert prop in soup_doc_type.properties, \
            f"SOUP missing required property: {prop}"
    
    # Verify lifecycle states
    assert hasattr(soup_doc_type, 'lifecycle'), "SOUP should have lifecycle defined"
    lifecycle = soup_doc_type.lifecycle
    assert isinstance(lifecycle, dict), "Lifecycle should be a dictionary"
    
    # Verify required states
    states = lifecycle.get('states', [])
    state_ids = [state['id'] for state in states]
    required_states = ["draft", "under_review", "approved"]
    for state in required_states:
        assert state in state_ids, f"SOUP lifecycle missing required state: {state}"
    
    # Verify transitions exist
    transitions = lifecycle.get('transitions', [])
    assert len(transitions) > 0, "SOUP should have lifecycle transitions"


def test_TC_DOCGEN_001_001_document_generator_exists():
    """
    Verify Document Generator Module Exists
    
    @test_id: TC-DOCGEN-001-001
    
    Verify that document generator module is available for PDF export.
    """
    # Check that document generator module exists
    doc_gen_path = Path(__file__).parent.parent / "src" / "traceability" / "document_generator.py"
    assert doc_gen_path.exists(), "document_generator.py module not found"
    
    # Try to import it
    from traceability.document_generator import DocumentGenerator
    assert DocumentGenerator is not None, "DocumentGenerator class not found"


def test_TC_REL_001_001_release_document_type():
    """
    Verify Release Document Type Configuration
    
    @test_id: TC-REL-001-001
    
    Verify that RELEASE document type is configured for release management.
    """
    # Initialize core
    dhf_root = Path(__file__).parent.parent / "DHF"
    core = CompliantFlowCore(dhf_root)
    
    # Verify RELEASE document type exists
    release_doc_type = core.config.get_doc_type("RELEASE")
    assert release_doc_type is not None, "RELEASE document type not found"
    
    # Verify basic properties
    assert "id" in release_doc_type.properties, "RELEASE missing id field"
    assert "title" in release_doc_type.properties, "RELEASE missing title field"
    
    # Verify lifecycle exists
    assert hasattr(release_doc_type, 'lifecycle'), "RELEASE should have lifecycle"


def test_TC_CORE_001_001_networkx_graph_structure():
    """
    Verify NetworkX DiGraph Data Structure
    
    @test_id: TC-CORE-001-001
    
    Verify that the system uses NetworkX DiGraph to store items as nodes
    and traceability links as edges.
    """
    # Initialize core
    dhf_root = Path(__file__).parent.parent / "DHF"
    core = CompliantFlowCore(dhf_root)
    
    # Verify graph exists
    assert core.graph is not None, "Graph not initialized"
    assert hasattr(core.graph, 'graph'), "Graph engine missing graph attribute"
    
    # Verify it's a NetworkX DiGraph
    import networkx as nx
    G = core.graph.graph
    assert isinstance(G, nx.DiGraph), "Graph should be NetworkX DiGraph"
    
    # Verify nodes exist
    assert len(G.nodes()) > 0, "Graph should have nodes"
    
    # Verify edges exist (traceability links)
    assert len(G.edges()) > 0, "Graph should have edges (traceability links)"


def test_TC_TRACE_001_001_traceability_matrix_configuration():
    """
    Verify Traceability Matrix Configuration
    
    @test_id: TC-TRACE-001-001
    
    Verify that traceability matrices are configurable in project_config.yaml.
    """
    # Initialize core
    dhf_root = Path(__file__).parent.parent / "DHF"
    core = CompliantFlowCore(dhf_root)
    
    # Verify config has traceability_matrices
    assert hasattr(core.config, 'traceability_matrices'), \
        "Config missing traceability_matrices"
    
    matrices = core.config.traceability_matrices
    assert isinstance(matrices, list), "traceability_matrices should be a list"
    assert len(matrices) > 0, "Should have at least one traceability matrix configured"
    
    # Verify matrix structure
    for matrix in matrices:
        assert hasattr(matrix, 'name'), "Matrix missing name"
        # Matrix uses 'path' instead of 'from_type'/'to_type'
        assert hasattr(matrix, 'path'), "Matrix missing path"
        assert isinstance(matrix.path, list), "Matrix path should be a list"
        assert len(matrix.path) >= 2, "Matrix path should have at least 2 doc types"
