"""
Shared test data fixtures for browser tests.

Provides common test DHF setup and data population functions
that can be used by both CRS and SYS browser tests.
"""

import shutil
import tempfile
from pathlib import Path
from typing import Dict, List
import yaml


def create_test_dhf() -> Path:
    """
    Create isolated test DHF directory with proper configuration.
    
    Creates minimal test config from scratch (not copying from production).
    
    Returns:
        Path to the created test DHF directory
    """
    # Create temp directory
    test_dir = Path(tempfile.mkdtemp(prefix="test_dhf_"))
    
    print(f"\n[SETUP] Creating test DHF directory: {test_dir}")
    
    # Create minimal test configuration from scratch
    test_config_dir = test_dir / "config"
    test_config_dir.mkdir(parents=True)
    
    # Create minimal project_config.yaml for testing
    # Only CR keeps explicit lifecycle; requirement types use GitOps model
    test_config = {
        'change_control': {
            'enabled': True,
            'change_request_type': 'CR',
            'affected_items_field': 'affected_items',
        },
        'global_lifecycle': {
            'states': [
                {'id': 'draft', 'label': 'Draft', 'action_label': 'Create', 'icon': '📝', 'color': 'warning'},
                {'id': 'under_review', 'label': 'Under Review', 'action_label': 'Submit for Review', 'icon': '👀', 'color': 'info'},
                {'id': 'approved', 'label': 'Approved', 'action_label': 'Approve', 'icon': '✅', 'color': 'success', 'is_stable': True}
            ]
        },
        'doc_types': [
            {
                'code': 'UC',
                'name': 'Use Case',
                'prefix': 'UC-',
                'directory': '00_uc',
                'icon': '👤',
                'page_enabled': True,
                'page_number': 4,
                'properties': [
                    'id',
                    {'name': 'title', 'format': 'short_text', 'label': 'Title'},
                    {'name': 'content', 'format': 'long_text', 'label': 'Content'},
                ],
            },
            {
                'code': 'CRS',
                'name': 'Customer Requirement',
                'prefix': 'CRS-',
                'directory': '01_req_crs',
                'icon': '🎯',
                'page_enabled': True,
                'page_number': 5,
                'properties': [
                    'id',
                    {'name': 'title', 'format': 'short_text', 'label': 'Title'},
                    {'name': 'content', 'format': 'long_text', 'label': 'Content'},
                    {'name': 'derives_from', 'format': 'relationship', 'target_types': ['UC'], 'label': 'Derives From'},
                ],
            },
            {
                'code': 'SYS',
                'name': 'System Requirement',
                'prefix': 'SYS-',
                'directory': '02_req_sys',
                'icon': '⚙️',
                'page_enabled': True,
                'page_number': 6,
                'properties': [
                    'id',
                    {'name': 'title', 'format': 'short_text', 'label': 'Title'},
                    {'name': 'content', 'format': 'long_text', 'label': 'Content'},
                    {'name': 'category', 'format': 'short_text', 'label': 'Category'},
                    {'name': 'derives_from', 'format': 'relationship', 'target_types': ['CRS'], 'label': 'Derives From'},
                ],
            },
            {
                'code': 'SRS',
                'name': 'Software Requirement',
                'prefix': 'SRS-',
                'directory': '03_req_srs',
                'icon': '💻',
                'page_enabled': True,
                'page_number': 7,
                'properties': [
                    'id',
                    {'name': 'title', 'format': 'short_text', 'label': 'Title'},
                    {'name': 'content', 'format': 'long_text', 'label': 'Content'},
                    {'name': 'derives_from', 'format': 'relationship', 'target_types': ['SYS'], 'label': 'Derives From'},
                ],
            },
            {
                'code': 'SYSARCH',
                'name': 'System Architecture',
                'prefix': 'SYSARCH-',
                'directory': '07_sysarch',
                'icon': '🏗️',
                'page_enabled': True,
                'page_number': 8,
                'properties': [
                    'id',
                    {'name': 'title', 'format': 'short_text', 'label': 'Title'},
                    {'name': 'content', 'format': 'long_text', 'label': 'Content'},
                    {'name': 'implements', 'format': 'relationship', 'target_types': ['SYS'], 'label': 'Implements'},
                ],
            },
            {
                'code': 'CR',
                'name': 'Change Request',
                'prefix': 'CR-',
                'directory': '08_cr',
                'icon': '📝',
                'page_enabled': True,
                'page_number': 9,
                'properties': [
                    'id',
                    {'name': 'title', 'format': 'short_text', 'label': 'Title'},
                    {'name': 'description', 'format': 'long_text', 'label': 'Description'},
                    {'name': 'justification', 'format': 'long_text', 'label': 'Justification'},
                    {'name': 'affected_items', 'format': 'relationship', 'label': 'Affected Items'},
                    {'name': 'implementation_prs', 'format': 'relationship', 'label': 'Implementation PRs'},
                ],
                'lifecycle': {
                    'transitions': [
                        {'from_states': [None], 'to_state': 'draft'},
                        {'from_states': ['draft'], 'to_state': 'approved'},
                        {'from_states': ['draft'], 'to_state': 'rejected'}
                    ]
                }
            }
        ]
    }
    
    config_file = test_config_dir / "project_config.yaml"
    with open(config_file, 'w') as f:
        yaml.dump(test_config, f, default_flow_style=False, sort_keys=False)
    
    print(f"[OK] Created minimal test config with {len(test_config['doc_types'])} document types")
    
    # Create directory structure for all document types
    doc_type_dirs = [
        "00_uc", "01_req_crs", "02_req_sys", "03_req_srs",
        "04_req_sds", "05_swdd", "06_swad", "07_sysarch",
        "08_cr", "09_risk", "10_rcm", "11_tc",
    ]
    
    items_dir = test_dir / "items"
    items_dir.mkdir(parents=True)
    
    for doc_dir in doc_type_dirs:
        (items_dir / doc_dir).mkdir(parents=True, exist_ok=True)
    
    # Create documents directory structure
    (test_dir / "documents" / "specifications" / "templates").mkdir(parents=True)

    # Create governance directory for compliance policies
    governance_dir = test_dir / "governance"
    governance_dir.mkdir(parents=True)

    print(f"[OK] Created directory structure for {len(doc_type_dirs)} document types")

    return test_dir


def get_test_dataset() -> List[Dict]:
    """
    Get minimal test dataset for browser tests.
    
    Returns complete traceability chain and supporting items.
    
    Returns:
        List of item dictionaries ready for CompliantFlowCore.create_item()
    """
    return [
        # User Needs (no status — GitOps model)
        {
            'id': 'UC-001',
            'title': 'User Need - Test Item',
            'content': 'User needs test functionality',
        },
        # Customer Requirements (no status — GitOps model)
        {
            'id': 'CRS-001',
            'title': 'Customer Requirement - Test Item',
            'content': 'Customer requires test feature',
            'derives_from': ['UC-001'],
        },
        # System Requirements (no status — GitOps model)
        {
            'id': 'SYS-001',
            'title': 'System Requirement - Test Item',
            'content': 'System shall provide test capability',
            'derives_from': ['CRS-001'],
        },
        {
            'id': 'SYS-002',
            'title': 'Draft System Requirement',
            'content': 'System shall perform function X',
            'category': 'Functional',
            'derives_from': ['CRS-001'],
        },
        # Software Requirements (no status — GitOps model)
        {
            'id': 'SRS-001',
            'title': 'Item Persistence and Versioning',
            'content': 'Software shall persist items to YAML files with version control',
            'derives_from': ['SYS-001'],
        },
        {
            'id': 'SRS-002',
            'title': 'Graph-based Traceability',
            'content': 'Software shall provide graph-based traceability visualization',
            'derives_from': ['SYS-001'],
        },
        # System Architecture (no status — GitOps model)
        {
            'id': 'SYSARCH-001',
            'title': 'System Architecture Component',
            'content': 'Architecture component for test system',
            'implements': ['SYS-001'],
        },
        # Change Requests (explicit lifecycle: draft → approved)
        {
            'id': 'CR-001',
            'title': 'Test Change Request',
            'description': 'Change request for testing purposes',
            'justification': 'Testing CR workflow',
            'status': 'draft',
            'affected_items': ['SRS-001'],
        },
    ]


def populate_governance(test_dhf_root: Path):
    """
    Create governance directory with IEC 62304 test policies.

    Args:
        test_dhf_root: Path to the test DHF directory
    """
    governance_dir = test_dhf_root / "governance"
    governance_dir.mkdir(parents=True, exist_ok=True)

    # Create IEC 62304 policy group with minimal test policies
    # Must match PolicyGroup and Policy model schemas
    iec_62304_policy = {
        'id': 'IEC_62304',  # Required: ID of the policy group
        'title': 'IEC 62304 Medical Device Software',  # Required
        'type': 'standard',  # Optional: regulation, procedure, or standard
        'version': '2015',  # Optional
        'policies': [  # Required: List of Policy objects
            {
                'id': '5.1.1',  # Required: Unique ID
                'section': '5.1.1',  # Required: Section reference
                'text': 'All software requirements shall be traceable to system requirements',  # Required
                'status': 'approved'  # Literal: approved, draft, or rejected
            },
            {
                'id': '5.1.3',
                'section': '5.1.3',
                'text': 'All software requirements shall have verification criteria',
                'status': 'approved'
            },
            {
                'id': '5.3.1',
                'section': '5.3.1',
                'text': 'Software architecture shall be documented',
                'status': 'approved'
            },
            {
                'id': '5.5.2',
                'section': '5.5.2',
                'text': 'All software units shall be tested',
                'status': 'approved'
            },
            {
                'id': '6.2.1',
                'section': '6.2.1',
                'text': 'Change requests shall track affected items',
                'status': 'approved'
            }
        ]
    }

    # Write IEC_62304.yaml
    iec_file = governance_dir / "IEC_62304.yaml"
    with open(iec_file, 'w') as f:
        yaml.dump(iec_62304_policy, f, default_flow_style=False, sort_keys=False)

    print(f"[OK] Created governance policies: IEC_62304.yaml with {len(iec_62304_policy['policies'])} policies")


def populate_test_dhf(test_dhf_root: Path):
    """
    Populate test DHF with minimal dataset.

    Creates test items programmatically through CompliantFlowCore API.

    Args:
        test_dhf_root: Path to the test DHF directory

    Returns:
        CompliantFlowCore instance with populated data
    """
    from compliantflow.core import CompliantFlowCore

    print(f"\n[DATA] Populating test DHF with test data...")

    # Populate governance policies first
    populate_governance(test_dhf_root)

    # Initialize core with test DHF (no auto-commit for tests)
    core = CompliantFlowCore(test_dhf_root, auto_commit=False)

    # Get test dataset
    test_items = get_test_dataset()

    # Create all test items
    for item_data in test_items:
        try:
            core.create_item(item_data)
            print(f"  [OK] Created {item_data['id']}")
        except Exception as e:
            print(f"  [WARN] Failed to create {item_data['id']}: {e}")
            import traceback
            traceback.print_exc()

    print(f"[OK] Test DHF populated with {len(test_items)} items")

    # Refresh to ensure graph consistency
    core.refresh()

    return core
