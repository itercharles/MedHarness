"""Shared fixtures for user workflow tests."""
import pytest
from pathlib import Path
from src.traceability.compliant_flow_core import CompliantFlowCore


@pytest.fixture
def test_dhf(tmp_path):
    """Create minimal test DHF structure with config and directories."""
    dhf_path = tmp_path / "DHF"
    dhf_path.mkdir()
    
    # Create config directory
    config_dir = dhf_path / "config"
    config_dir.mkdir()
    
    # Create minimal project_config.yaml
    config_file = config_dir / "project_config.yaml"
    config_content = """
project:
  name: "Test Project"
  version: "1.0.0"

doc_types:
  - code: SYS
    name: "System Requirement"
    prefix: "SYS-"
    directory: "01_sys"
    properties: ["id", "title", "content", "category", "derives_from"]
    
    lifecycle:
      states:
        - id: draft
          label: "Draft"
          is_initial: true
        - id: under_review
          label: "Under Review"
        - id: approved
          label: "Approved"
          is_stable: true
      
      transitions:
        - from: draft
          to: under_review
          label: "Submit for Review"
        - from: under_review
          to: approved
          label: "Approve"
        - from: under_review
          to: draft
          label: "Reject"
    
    relations:
      - name: derives_from
        target: CRS
        label: "Derives From"
        reverse_name: derived_by
  
  - code: SRS
    name: "Software Requirement"
    prefix: "SRS-"
    directory: "02_srs"
    properties: ["id", "title", "content", "derives_from"]
    
    lifecycle:
      states:
        - {id: draft, label: "Draft", is_initial: true}
        - {id: approved, label: "Approved", is_stable: true}
      transitions:
        - {from: draft, to: approved, label: "Approve"}
    
    relations:
      - name: derives_from
        target: SYS
        label: "Derives From"
        reverse_name: derived_by
  
  - code: CR
    name: "Change Request"
    prefix: "CR-"
    directory: "09_cr"
    properties: ["id", "title", "description", "affected_items", "justification"]
    
    lifecycle:
      states:
        - {id: submitted, label: "Submitted", is_initial: true}
        - {id: under_review, label: "Under Review"}
        - {id: approved, label: "Approved", is_stable: true}
        - {id: rejected, label: "Rejected", is_stable: true}
      transitions:
        - {from: submitted, to: under_review, label: "Start Review"}
        - {from: under_review, to: approved, label: "Approve"}
        - {from: under_review, to: rejected, label: "Reject"}
"""
    config_file.write_text(config_content)
    
    # Create items directory structure
    items_dir = dhf_path / "items"
    items_dir.mkdir()
    (items_dir / "01_sys").mkdir()
    (items_dir / "02_srs").mkdir()
    (items_dir / "09_cr").mkdir()
    
    return dhf_path


@pytest.fixture
def test_core(test_dhf):
    """Initialize CompliantFlowCore with test DHF."""
    return CompliantFlowCore(repo_root=test_dhf)


@pytest.fixture
def draft_sys_item(test_core):
    """Create a draft SYS requirement for testing."""
    data = {
        'id': 'SYS-001',
        'title': 'Test System Requirement',
        'content': 'The system shall perform function X',
        'category': 'Functional',
        'status': 'draft'
    }
    return test_core.create_item(data)


@pytest.fixture
def approved_sys_item(test_core):
    """Create an approved (stable) SYS requirement."""
    data = {
        'id': 'SYS-002',
        'title': 'Approved System Requirement',
        'content': 'The system shall perform function Y',
        'category': 'Functional',
        'status': 'approved',
        'approved_by': 'test_user',
        'approved_date': '2025-01-01T00:00:00'
    }
    return test_core.create_item(data)


@pytest.fixture
def multiple_sys_items(test_core):
    """Create multiple SYS items for relationship testing."""
    items = []
    for i in range(1, 4):
        data = {
            'id': f'SYS-{i:03d}',
            'title': f'System Requirement {i}',
            'content': f'The system shall perform function {i}',
            'status': 'draft'
        }
        items.append(test_core.create_item(data))
    return items
