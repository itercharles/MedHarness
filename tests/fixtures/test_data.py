"""
Shared test data fixtures for browser tests.

Provides common test DHF setup and data population functions
that can be used by both CRS and SYS browser tests.
"""

import shutil
import tempfile
from pathlib import Path
from typing import Dict, List


def create_test_dhf() -> Path:
    """
    Create isolated test DHF directory with proper configuration.
    
    Copies project_config.yaml from production and creates directory structure.
    
    Returns:
        Path to the created test DHF directory
    """
    # Create temp directory
    test_dir = Path(tempfile.mkdtemp(prefix="test_dhf_"))
    
    print(f"\n[SETUP] Creating test DHF directory: {test_dir}")
    
    # Get production DHF path
    production_dhf = Path(__file__).parent.parent.parent / "DHF"
    
    # Copy project configuration from production
    prod_config_dir = production_dhf / "config"
    test_config_dir = test_dir / "config"
    shutil.copytree(prod_config_dir, test_config_dir)
    print(f"[OK] Copied project config from production")
    
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
            'status': 'approved'
        },
        # Customer Requirements
        {
            'id': 'CRS-001',
            'title': 'Customer Requirement - Test Item',
            'content': 'Customer requires test feature',
            'status': 'approved',
            'derives_from': ['UC-001']
        },
        # System Requirements
        {
            'id': 'SYS-001',
            'title': 'System Requirement - Test Item',
            'content': 'System shall provide test capability',
            'status': 'approved',
            'derives_from': ['CRS-001']
        },
        # Software Requirements
        {
            'id': 'SRS-001',
            'title': 'Item Persistence and Versioning',
            'content': 'Software shall persist items to YAML files with version control',
            'status': 'approved',
            'derives_from': ['SYS-001']
        },
        # System Architecture
        {
            'id': 'SYSARCH-001',
            'title': 'System Architecture Component',
            'content': 'Architecture component for test system',
            'status': 'approved',
            'implements': ['SYS-001']
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
    from traceability.compliant_flow_core import CompliantFlowCore
    
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
