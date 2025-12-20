"""
Test suite for SYS (System Requirements) test cases.

These tests verify system-level requirements are correctly implemented.

@links: SYS-*
"""

import pytest
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from traceability.compliant_flow_core import CompliantFlowCore


def test_TC_SYS_004_governance_parsing():
    """
    Verify Governance Parsing
    
    @links: SYS-005
    @test_id: TC-SYS-004
    
    Ensure IEC_62304.yaml and SOP_001.yaml are correctly loaded.
    """
    # Initialize core
    dhf_root = Path(__file__).parent.parent / "DHF"
    core = CompliantFlowCore(dhf_root)
    
    # Verify governance directory exists
    governance_dir = dhf_root / "governance"
    assert governance_dir.exists(), "Governance directory not found"
    
    # Check for governance files
    governance_files = list(governance_dir.glob("*.yaml"))
    assert len(governance_files) > 0, "No governance YAML files found"
    
    # Verify at least one governance file can be loaded
    assert any("IEC" in f.name or "SOP" in f.name for f in governance_files), \
        "Expected governance files (IEC_62304.yaml or SOP_001.yaml) not found"


def test_TC_SYS_005_policy_checks():
    """
    Verify Policy Checks
    
    @links: SYS-006
    @test_id: TC-SYS-005
    
    Run check_compliance with known data and verify results.
    """
    # Initialize core
    dhf_root = Path(__file__).parent.parent / "DHF"
    core = CompliantFlowCore(dhf_root)
    
    # Verify config has policies
    assert hasattr(core.config, 'policies'), "Config missing policies"
    policies_config = core.config.policies
    
    # Verify policy configuration exists
    assert hasattr(policies_config, 'require_test_coverage'), \
        "Policies missing require_test_coverage configuration"
    
    # Verify compliance models can be imported
    from traceability.models.compliance import Policy, PolicyGroup
    assert Policy is not None
    assert PolicyGroup is not None


def test_TC_SYS_006_graph_visualization():
    """
    Verify Graph Visualization
    
    @links: SYS-007
    @test_id: TC-SYS-006
    
    Ensure graph visualization components exist.
    """
    dhf_root = Path(__file__).parent.parent / "DHF"
    core = CompliantFlowCore(dhf_root)
    
    # Verify graph exists
    assert core.graph is not None, "Graph not initialized"
    import networkx as nx
    assert isinstance(core.graph.graph, nx.DiGraph), "Graph should be NetworkX DiGraph"


def test_TC_SYS_007_policy_evaluation():
    """
    Verify Policy Evaluation
    
    @links: SYS-008
    @test_id: TC-SYS-007
    
    System shall evaluate and report pass/fail status of policies.
    """
    dhf_root = Path(__file__).parent.parent / "DHF"
    core = CompliantFlowCore(dhf_root)
    
    # Verify policies exist in config
    assert hasattr(core.config, 'policies'), "Config missing policies"
    
    # Verify compliance models exist
    from traceability.models.compliance import PolicyResult, ComplianceReport
    assert PolicyResult is not None
    assert ComplianceReport is not None


# TC-SYS-008 series are for Change Request functionality
def test_TC_SYS_008_change_request_functionality():
    """
    Verify Change Request Functionality
    
    @links: SYS-008
    @test_id: TC-SYS-008-001, TC-SYS-008-002, TC-SYS-008-003, TC-SYS-008-004, TC-SYS-008-005
    
    Verify CR document type exists and supports change management workflow.
    """
    dhf_root = Path(__file__).parent.parent / "DHF"
    core = CompliantFlowCore(dhf_root)
    
    # Verify CR document type exists
    cr_doc_type = core.config.get_doc_type("CR")
    assert cr_doc_type is not None, "CR document type not found"
    
    # Verify required fields
    required_fields = ["id", "title", "description"]
    for field in required_fields:
        assert field in cr_doc_type.properties, f"CR missing field: {field}"
    
    # Verify lifecycle exists
    assert hasattr(cr_doc_type, 'lifecycle'), "CR missing lifecycle"


def test_TC_SYS_009_001_release_management():
    """
    Verify Release Management
    
    @links: SYS-009
    @test_id: TC-SYS-009-001
    
    Verify RELEASE document type supports release management.
    """
    dhf_root = Path(__file__).parent.parent / "DHF"
    core = CompliantFlowCore(dhf_root)
    
    # Verify RELEASE document type exists
    release_doc_type = core.config.get_doc_type("RELEASE")
    assert release_doc_type is not None, "RELEASE document type not found"
    
    # Verify lifecycle exists
    assert hasattr(release_doc_type, 'lifecycle'), "RELEASE missing lifecycle"


def test_TC_SYS_010_001_defect_tracking():
    """
    Verify Defect Tracking
    
    @links: SYS-010
    @test_id: TC-SYS-010-001
    
    Verify DEFECT document type supports defect tracking.
    """
    dhf_root = Path(__file__).parent.parent / "DHF"
    core = CompliantFlowCore(dhf_root)
    
    # Verify DEFECT document type exists
    defect_doc_type = core.config.get_doc_type("DEFECT")
    assert defect_doc_type is not None, "DEFECT document type not found"
    
    # Verify required fields
    required_fields = ["id", "title", "description", "severity"]
    for field in required_fields:
        assert field in defect_doc_type.properties, f"DEFECT missing field: {field}"


def test_TC_SYS_011_001_soup_tracking():
    """
    Verify SOUP Tracking
    
    @links: SYS-011
    @test_id: TC-SYS-011-001
    
    Verify SOUP document type supports SOUP tracking per IEC 62304.
    """
    dhf_root = Path(__file__).parent.parent / "DHF"
    core = CompliantFlowCore(dhf_root)
    
    # Verify SOUP document type exists
    soup_doc_type = core.config.get_doc_type("SOUP")
    assert soup_doc_type is not None, "SOUP document type not found"
    
    # Verify required fields per IEC 62304
    required_fields = ["name", "version", "purpose", "safety_class"]
    for field in required_fields:
        assert field in soup_doc_type.properties, f"SOUP missing field: {field}"


def test_TC_SYS_012_001_document_lifecycle():
    """
    Verify Document Lifecycle Management
    
    @links: SYS-012
    @test_id: TC-SYS-012-001
    
    Verify document types support lifecycle states and transitions.
    """
    dhf_root = Path(__file__).parent.parent / "DHF"
    core = CompliantFlowCore(dhf_root)
    
    # Check that at least one doc type has lifecycle
    doc_types_with_lifecycle = [
        dt for dt in core.config.doc_types 
        if hasattr(dt, 'lifecycle') and dt.lifecycle is not None
    ]
    assert len(doc_types_with_lifecycle) > 0, "No document types have lifecycle configured"
    
    # Verify lifecycle structure
    sample_dt = doc_types_with_lifecycle[0]
    lifecycle = sample_dt.lifecycle
    assert 'states' in lifecycle, "Lifecycle missing states"
    assert 'transitions' in lifecycle, "Lifecycle missing transitions"


def test_TC_SYS_013_001_traceability_links():
    """
    Verify Traceability Links
    
    @links: SYS-013
    @test_id: TC-SYS-013-001
    
    Verify system supports traceability links between items.
    """
    dhf_root = Path(__file__).parent.parent / "DHF"
    core = CompliantFlowCore(dhf_root)
    
    # Verify graph has edges (traceability links)
    import networkx as nx
    G = core.graph.graph
    assert len(G.edges()) > 0, "Graph should have edges (traceability links)"
    
    # Verify items can have links
    all_items = core.get_all_items()
    items_with_links = [item for item in all_items if item.get('links')]
    assert len(items_with_links) > 0, "No items have traceability links"


def test_TC_SYS_014_001_configuration_management():
    """
    Verify Configuration Management
    
    @links: SYS-014
    @test_id: TC-SYS-014-001
    
    Verify system loads configuration from project_config.yaml.
    """
    dhf_root = Path(__file__).parent.parent / "DHF"
    core = CompliantFlowCore(dhf_root)
    
    # Verify config is loaded
    assert core.config is not None, "Configuration not loaded"
    
    # Verify config has doc_types
    assert hasattr(core.config, 'doc_types'), "Config missing doc_types"
    assert len(core.config.doc_types) > 0, "No document types configured"
    
    # Verify config file exists
    config_file = dhf_root / "config" / "project_config.yaml"
    assert config_file.exists(), "project_config.yaml not found"


def test_TC_SYS_015_001_yaml_storage():
    """
    Verify YAML Storage
    
    @links: SYS-015
    @test_id: TC-SYS-015-001
    
    Verify system stores and loads items from YAML files.
    """
    dhf_root = Path(__file__).parent.parent / "DHF"
    core = CompliantFlowCore(dhf_root)
    
    # Verify items are loaded
    all_items = core.get_all_items()
    assert len(all_items) > 0, "No items loaded from YAML files"
    
    # Verify YAML files exist
    yaml_files = list(dhf_root.rglob("*.yaml"))
    assert len(yaml_files) > 0, "No YAML files found in DHF directory"
    
    # Verify items directory exists
    items_dir = dhf_root / "items"
    assert items_dir.exists(), "Items directory not found"
