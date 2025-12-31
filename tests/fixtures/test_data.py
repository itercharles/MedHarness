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
    
    # Create minimal project_config.yaml for testing with lifecycle
    test_config = {
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
                    {'name': 'status', 'format': 'select', 'label': 'Status', 'options': ['draft', 'approved']}
                ],
                'lifecycle': {
                    'states': [
                        {'id': 'draft', 'label': 'Draft', 'is_initial': True, 'icon': '📝', 'color': 'warning'},
                        {'id': 'approved', 'label': 'Approved', 'is_stable': True, 'icon': '✅', 'color': 'success'}
                    ]
                }
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
                    {'name': 'status', 'format': 'select', 'label': 'Status', 'options': ['draft', 'approved']}
                ],
                'lifecycle': {
                    'states': [
                        {'id': 'draft', 'label': 'Draft', 'is_initial': True, 'icon': '📝', 'color': 'warning'},
                        {'id': 'approved', 'label': 'Approved', 'is_stable': True, 'icon': '✅', 'color': 'success'}
                    ]
                }
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
                    {'name': 'status', 'format': 'select', 'label': 'Status', 'options': ['draft', 'under_review', 'approved']}
                ],
                'lifecycle': {
                    'states': [
                        {'id': 'draft', 'label': 'Draft', 'is_initial': True, 'icon': '📝', 'color': 'warning'},
                        {'id': 'under_review', 'label': 'Under Review', 'icon': '👀', 'color': 'info'},
                        {'id': 'approved', 'label': 'Approved', 'is_stable': True, 'icon': '✅', 'color': 'success'}
                    ],
                    'transitions': [
                        {'from': 'draft', 'to': 'under_review', 'label': 'Submit for Review'},
                        {'from': 'under_review', 'to': 'approved', 'label': 'Approve'},
                        {'from': 'under_review', 'to': 'draft', 'label': 'Reject'}
                    ]
                }
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
                    {'name': 'status', 'format': 'select', 'label': 'Status', 'options': ['draft', 'approved']}
                ],
                'lifecycle': {
                    'states': [
                        {'id': 'draft', 'label': 'Draft', 'is_initial': True, 'icon': '📝', 'color': 'warning'},
                        {'id': 'approved', 'label': 'Approved', 'is_stable': True, 'icon': '✅', 'color': 'success'}
                    ]
                }
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
                    {'name': 'status', 'format': 'select', 'label': 'Status', 'options': ['draft', 'approved']}
                ],
                'lifecycle': {
                    'states': [
                        {'id': 'draft', 'label': 'Draft', 'is_initial': True, 'icon': '📝', 'color': 'warning'},
                        {'id': 'approved', 'label': 'Approved', 'is_stable': True, 'icon': '✅', 'color': 'success'}
                    ]
                }
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
                    {'name': 'status', 'format': 'select', 'label': 'Status', 'options': ['submitted', 'approved', 'rejected']}
                ],
                'lifecycle': {
                    'states': [
                        {'id': 'submitted', 'label': 'Submitted', 'is_initial': True, 'icon': '📝', 'color': 'warning'},
                        {'id': 'approved', 'label': 'Approved', 'is_stable': True, 'icon': '✅', 'color': 'success'},
                        {'id': 'rejected', 'label': 'Rejected', 'is_stable': True, 'icon': '❌', 'color': 'danger'}
                    ]
                }
            }
        ]
    }
    
    config_file = test_config_dir / "project_config.yaml"
    with open(config_file, 'w') as f:
        yaml.dump(test_config, f, default_flow_style=False, sort_keys=False)
    
    print(f"[OK] Created minimal test config with {len(test_config['doc_types'])} document types (with lifecycle)")
    
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
        # User Needs
        {
            'id': 'UC-001',
            'title': 'User Need - Test Item',
            'content': 'User needs test functionality',
            'status': 'approved',
            'approved_by': 'test_user',
            'approved_date': '2025-01-01T00:00:00'
        },
        # Customer Requirements
        {
            'id': 'CRS-001',
            'title': 'Customer Requirement - Test Item',
            'content': 'Customer requires test feature',
            'status': 'approved',
            'derives_from': ['UC-001'],
            'approved_by': 'test_user',
            'approved_date': '2025-01-01T00:00:00'
        },
        # System Requirements
        {
            'id': 'SYS-001',
            'title': 'System Requirement - Test Item',
            'content': 'System shall provide test capability',
            'status': 'approved',
            'derives_from': ['CRS-001'],
            'approved_by': 'test_user',
            'approved_date': '2025-01-01T00:00:00'
        },
        {
            'id': 'SYS-002',
            'title': 'Draft System Requirement',
            'content': 'System shall perform function X',
            'category': 'Functional',
            'status': 'draft',
            'derives_from': ['CRS-001']
        },
        # Software Requirements
        {
            'id': 'SRS-001',
            'title': 'Item Persistence and Versioning',
            'content': 'Software shall persist items to YAML files with version control',
            'status': 'approved',
            'derives_from': ['SYS-001'],
            'approved_by': 'test_user',
            'approved_date': '2025-01-01T00:00:00'
        },
        {
            'id': 'SRS-002',
            'title': 'Graph-based Traceability',
            'content': 'Software shall provide graph-based traceability visualization',
            'status': 'approved',
            'derives_from': ['SYS-001'],
            'approved_by': 'test_user',
            'approved_date': '2025-01-01T00:00:00'
        },
        # System Architecture
        {
            'id': 'SYSARCH-001',
            'title': 'System Architecture Component',
            'content': 'Architecture component for test system',
            'status': 'approved',
            'implements': ['SYS-001'],
            'approved_by': 'test_user',
            'approved_date': '2025-01-01T00:00:00'
        },
        # Change Requests
        {
            'id': 'CR-001',
            'title': 'Test Change Request',
            'description': 'Change request for testing purposes',
            'justification': 'Testing CR workflow',
            'status': 'submitted',
            'affected_items': ['SRS-001']
        },
    ]


def populate_test_dhf(test_dhf_root: Path):
    """
    Populate test DHF with minimal dataset.
    
    Creates test items programmatically through CompliantFlowCore API.
    
    Args:
        test_dhf_root: Path to the test DHF directory
        
    Returns:
        CompliantFlowCore instance with populated data
    """
    from src.traceability.compliant_flow_core import CompliantFlowCore
    
    print(f"\n[DATA] Populating test DHF with test data...")
    
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
    
    print(f"[OK] Test DHF populated with {len(test_items)} items")
    
    return core
