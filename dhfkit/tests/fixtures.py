"""
DHF utility test fixtures.

Provides test DHF creation and population helpers for DHF/utils tests.
Data is written via ItemSaver directly — no MedHarnessCore dependency.
"""

import tempfile
from pathlib import Path
from typing import Dict, List
import yaml


def create_test_dhf() -> Path:
    """
    Create isolated test DHF directory with proper configuration.

    Creates minimal test config from scratch (not copying from production).
    Uses split config format: global.yaml + doc_types/*.yaml

    Returns:
        Path to the created test DHF directory
    """
    project_root = Path(tempfile.mkdtemp(prefix="test_project_"))
    test_dir = project_root / "DHF"
    test_dir.mkdir()

    config_dir = test_dir / "config"
    config_dir.mkdir(parents=True)
    doc_types_dir = config_dir / "doc_types"
    doc_types_dir.mkdir(parents=True)

    # --- global.yaml ---
    global_config = {
        'change_control': {
            'enabled': True,
            'change_request_type': 'CR',
            'affected_items_field': 'affected_items',
        },
        'global_lifecycle': {
            'states': [
                {'id': 'draft', 'label': 'Draft', 'action_label': 'Create', 'icon': '📝', 'color': 'warning'},
                {'id': 'under_review', 'label': 'Under Review', 'action_label': 'Submit for Review', 'icon': '👀', 'color': 'info'},
                {'id': 'approved', 'label': 'Approved', 'action_label': 'Approve', 'icon': '✅', 'color': 'success', 'is_stable': True},
                {'id': 'rejected', 'label': 'Rejected', 'action_label': 'Reject', 'icon': '❌', 'color': 'error', 'is_stable': True},
            ]
        },
        'traceability_matrices': [
            {
                'name': 'Requirements Chain',
                'description': 'Full requirements traceability chain',
                'path': ['UC', 'CRS', 'SYS', 'SRS'],
            }
        ],
        'document_specifications': {
            'SYS': {
                'template': 'requirements_specification.md.j2',
                'output': 'DHF/documents/specifications/SYS/system_requirement_specification.md',
                'doc_type_name': 'System Requirement',
            },
            'CRS': {
                'template': 'customer_requirement_specification.md.j2',
                'output': 'DHF/documents/specifications/CRS/customer_requirement_specification.md',
                'doc_type_name': 'Customer Requirement',
            },
        },
        'test_integration': {
            'result_store': {'path': 'test-results/results.yaml'},
        },
    }

    with open(config_dir / "global.yaml", 'w') as f:
        yaml.dump(global_config, f, default_flow_style=False, sort_keys=False)

    # --- Minimal Jinja2 templates for doc generation ---
    specs_dir = test_dir / "documents" / "specs"
    specs_dir.mkdir(parents=True, exist_ok=True)
    (specs_dir / "requirements_specification.md.j2").write_text(
        "# Requirements Specification\n\n## {{ doc_type_name }}\n\n| ID | Title | Status |\n|---|---|---|\n{% for item in items %}| {{ item.id }} | {{ item.title }} | Verified |\n{% endfor %}\n"
    )
    (specs_dir / "customer_requirement_specification.md.j2").write_text(
        "# Customer Requirement Specification\n\n## {{ doc_type_name }}\n\n| ID | Title | Status |\n|---|---|---|\n{% for item in items %}| {{ item.id }} | {{ item.title }} | — |\n{% endfor %}\n"
    )

    # --- doc_types/*.yaml ---
    doc_type_configs = [
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
            'directory': '01_crs',
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
            'directory': '02_sys',
            'icon': '⚙️',
            'page_enabled': True,
            'page_number': 6,
            'has_verification': True,
            'verification_states': ['not_verified', 'verified', 'failed'],
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
            'directory': '03_srs',
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
                    {'from_states': ['draft'], 'to_state': 'rejected'},
                ]
            }
        },
    ]

    for dt_config in doc_type_configs:
        code = dt_config['code'].lower()
        with open(doc_types_dir / f"{code}.yaml", 'w') as f:
            yaml.dump(dt_config, f, default_flow_style=False, sort_keys=False)

    # Create directory structure for document types
    doc_type_dirs = [
        "00_uc", "01_crs", "02_sys", "03_srs",
        "04_req_sds", "04_swdd", "06_swad", "07_sysarch",
        "08_cr", "09_risk", "10_rcm", "11_tc",
    ]

    items_dir = test_dir / "items"
    items_dir.mkdir(parents=True)

    for doc_dir in doc_type_dirs:
        (items_dir / doc_dir).mkdir(parents=True, exist_ok=True)

    return test_dir


def get_test_dataset() -> List[Dict]:
    """
    Get minimal test dataset for DHF utility tests.

    Returns complete traceability chain and supporting items.
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
def populate_test_dhf_direct(test_dhf_root: Path) -> Path:
    """
    Populate test DHF with minimal dataset using ItemSaver directly.

    Writes items via ItemSaver (utils layer only) — no MedHarnessCore dependency.

    Returns:
        test_dhf_root (for chaining)
    """
    from dhfkit.models.config import ProjectConfig
    from dhfkit.models.item import Item
    from dhfkit.repository.saver import ItemSaver


    config = ProjectConfig.load(test_dhf_root / "config")
    # git_repo=None → no auto-commit; items are written directly as YAML files
    saver = ItemSaver(test_dhf_root / "items", git_repo=None, project_config=config)

    for item_data in get_test_dataset():
        try:
            item = Item.model_validate(item_data)
            saver.save(item)
        except Exception as e:
            print(f"  [WARN] Failed to save {item_data['id']}: {e}")

    return test_dhf_root
