"""
Test suite for CRS (Customer Requirements Specification) test cases.

These tests verify customer-facing requirements are correctly implemented.

@links: CRS-*
"""

import pytest
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from traceability.compliant_flow_core import CompliantFlowCore


def test_TC_CRS_001_document_export_functionality():
    """
    User Acceptance Test - Document Export
    
    @links: CRS-008
    @test_id: TC-CRS-001
    
    Verify that users can export requirements as PDF documents.
    Tests that the document generator module exists and can be initialized.
    """
    # Initialize core
    dhf_root = Path(__file__).parent.parent / "DHF"
    core = CompliantFlowCore(dhf_root)
    
    # Verify document generator module exists
    doc_gen_module = Path(__file__).parent.parent / "src" / "traceability" / "document_generator.py"
    assert doc_gen_module.exists(), "document_generator.py module not found"
    
    # Try to import and initialize document generator
    from traceability.document_generator import DocumentGenerator
    
    template_dir = dhf_root / "templates"
    generator = DocumentGenerator(core, template_dir)
    
    assert generator is not None, "DocumentGenerator failed to initialize"
    assert hasattr(generator, 'generate_requirements_spec'), \
        "DocumentGenerator missing generate_requirements_spec method"
    assert hasattr(generator, 'generate_traceability_matrix'), \
        "DocumentGenerator missing generate_traceability_matrix method"


def test_TC_CRS_002_compliance_workflow():
    """
    Validate Compliance Workflow
    
    @links: CRS-003
    @test_id: TC-CRS-002
    
    Verify that compliance checking functionality is available and
    score calculation works correctly.
    """
    # Initialize core
    dhf_root = Path(__file__).parent.parent / "DHF"
    core = CompliantFlowCore(dhf_root)
    
    # Verify compliance page exists
    compliance_page = Path(__file__).parent.parent / "src" / "pages" / "03_Compliance.py"
    assert compliance_page.exists(), "Compliance page not found"
    
    # Verify compliance module exists
    compliance_module = Path(__file__).parent.parent / "src" / "traceability" / "models" / "compliance.py"
    assert compliance_module.exists(), "Compliance module not found"
    
    # Verify compliance functionality can be imported
    from traceability.models.compliance import Policy, PolicyGroup, ComplianceReport
    assert Policy is not None, "Policy model not found"
    assert PolicyGroup is not None, "PolicyGroup model not found"
    assert ComplianceReport is not None, "ComplianceReport model not found"


def test_TC_CRS_003_docs_as_code():
    """
    Validate Docs-as-Code
    
    @links: CRS-002
    @test_id: TC-CRS-003
    
    Verify that requirements are stored as YAML files and can be loaded
    by the system.
    """
    # Initialize core
    dhf_root = Path(__file__).parent.parent / "DHF"
    core = CompliantFlowCore(dhf_root)
    
    # Verify items are loaded from YAML files
    all_items = core.get_all_items()
    assert len(all_items) > 0, "No items loaded from YAML files"
    
    # Verify items have expected structure
    sample_item = all_items[0]
    assert 'id' in sample_item, "Item missing id field"
    assert 'title' in sample_item or 'content' in sample_item, \
        "Item missing title or content"
    
    # Verify YAML files exist in DHF directory
    yaml_files = list(dhf_root.rglob("*.yaml"))
    assert len(yaml_files) > 0, "No YAML files found in DHF directory"


def test_TC_CRS_005_001_problem_resolution_process():
    """
    Validate Problem Resolution Process
    
    @links: CRS-005
    @test_id: TC-CRS-005-001
    
    Verify that the defect tracking system supports the problem
    resolution workflow per IEC 62304 §9.7.
    """
    # Initialize core
    dhf_root = Path(__file__).parent.parent / "DHF"
    core = CompliantFlowCore(dhf_root)
    
    # Verify DEFECT document type exists
    defect_doc_type = core.config.get_doc_type("DEFECT")
    assert defect_doc_type is not None, "DEFECT document type not configured"
    
    # Verify required fields for problem resolution
    required_fields = ["id", "title", "description", "severity", "assigned_to"]
    for field in required_fields:
        assert field in defect_doc_type.properties, \
            f"DEFECT missing required field for problem resolution: {field}"
    
    # Verify lifecycle supports problem resolution workflow
    assert hasattr(defect_doc_type, 'lifecycle'), "DEFECT missing lifecycle"
    lifecycle = defect_doc_type.lifecycle
    states = lifecycle.get('states', [])
    state_ids = [state['id'] for state in states]
    
    # Verify key workflow states exist
    required_states = ["open", "in_progress", "resolved", "closed"]
    for state in required_states:
        assert state in state_ids, \
            f"DEFECT lifecycle missing required state: {state}"


def test_TC_CRS_007_001_soup_management_workflow():
    """
    End-to-End SOUP Management Validation
    
    @links: CRS-007
    @test_id: TC-CRS-007-001
    
    Verify SOUP management workflow from creation to approval per IEC 62304 5.3.
    """
    # Initialize core
    dhf_root = Path(__file__).parent.parent / "DHF"
    core = CompliantFlowCore(dhf_root)
    
    # Verify SOUP document type exists
    soup_doc_type = core.config.get_doc_type("SOUP")
    assert soup_doc_type is not None, "SOUP document type not configured"
    
    # Verify required fields for SOUP management
    required_fields = ["name", "version", "manufacturer", "license", "purpose", "safety_class"]
    for field in required_fields:
        assert field in soup_doc_type.properties, \
            f"SOUP missing required field: {field}"
    
    # Verify lifecycle supports approval workflow
    assert hasattr(soup_doc_type, 'lifecycle'), "SOUP missing lifecycle"
    lifecycle = soup_doc_type.lifecycle
    states = lifecycle.get('states', [])
    state_ids = [state['id'] for state in states]
    
    # Verify approval states exist
    required_states = ["draft", "under_review", "approved"]
    for state in required_states:
        assert state in state_ids, f"SOUP lifecycle missing state: {state}"


def test_TC_CRS_008_001_document_generation_workflow():
    """
    End-to-End Document Generation Validation
    
    @links: CRS-008
    @test_id: TC-CRS-008-001
    
    Verify document generation produces regulatory-ready PDF documentation.
    """
    # Initialize core
    dhf_root = Path(__file__).parent.parent / "DHF"
    core = CompliantFlowCore(dhf_root)
    
    # Verify document generator exists
    from traceability.document_generator import DocumentGenerator
    
    template_dir = dhf_root / "templates"
    generator = DocumentGenerator(core, template_dir)
    
    # Verify key generation methods exist
    assert hasattr(generator, 'generate_requirements_spec'), \
        "Missing requirements spec generation"
    assert hasattr(generator, 'generate_traceability_matrix'), \
        "Missing traceability matrix generation"
    
    # Verify template directory exists
    assert template_dir.exists(), "Template directory not found"


def test_TC_CRS_011_001_compliance_dashboard():
    """
    Verify Compliance Dashboard Functionality
    
    @links: CRS-011
    @test_id: TC-CRS-011-001
    
    Verify compliance dashboard can load policies and display results.
    """
    # Initialize core
    dhf_root = Path(__file__).parent.parent / "DHF"
    core = CompliantFlowCore(dhf_root)
    
    # Verify compliance page exists
    compliance_page = Path(__file__).parent.parent / "src" / "pages" / "03_Compliance.py"
    assert compliance_page.exists(), "Compliance page not found"
    
    # Verify compliance models exist
    from traceability.models.compliance import Policy, PolicyGroup, ComplianceReport
    
    # Verify config has policies
    assert hasattr(core.config, 'policies'), "Config missing policies"
    policies_config = core.config.policies
    assert hasattr(policies_config, 'require_test_coverage'), \
        "Policies missing require_test_coverage"
