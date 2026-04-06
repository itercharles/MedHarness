"""
Shared test data fixtures for API tests.

Provides common test DHF setup and data population functions
that can be used by both CRS and SYS tests.
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

    print(f"\n[SETUP] Creating test DHF directory: {test_dir}")

    config_dir = test_dir / "config"
    config_dir.mkdir(parents=True)
    doc_types_dir = config_dir / "doc_types"
    doc_types_dir.mkdir(parents=True)

    # --- global.yaml ---
    global_config = {
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
        'document_specifications': {},
        'test_integration': {
            'result_store': {'path': 'test-results/results.yaml'},
        },
    }

    with open(config_dir / "global.yaml", 'w') as f:
        yaml.dump(global_config, f, default_flow_style=False, sort_keys=False)

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
            'code': 'RISK',
            'name': 'Risk Analysis',
            'prefix': 'RISK-',
            'directory': '09_risk',
            'icon': '⚠️',
            'page_enabled': True,
            'page_number': 12,
            'properties': [
                'id',
                {'name': 'title', 'format': 'short_text', 'label': 'Title'},
                {'name': 'hazard', 'format': 'long_text', 'label': 'Hazard'},
                {'name': 'cause', 'format': 'long_text', 'label': 'Cause'},
                {'name': 'effect', 'format': 'long_text', 'label': 'Effect'},
                {'name': 'severity_pre', 'format': 'select', 'options': ['S1', 'S2', 'S3', 'S4', 'S5'], 'label': 'Severity (pre)'},
                {'name': 'probability_pre', 'format': 'select', 'options': ['P1', 'P2', 'P3', 'P4', 'P5'], 'label': 'Probability (pre)'},
                {'name': 'severity_post', 'format': 'select', 'options': ['S1', 'S2', 'S3', 'S4', 'S5'], 'label': 'Severity (post)'},
                {'name': 'probability_post', 'format': 'select', 'options': ['P1', 'P2', 'P3', 'P4', 'P5'], 'label': 'Probability (post)'},
                {'name': 'risk_acceptability', 'format': 'select', 'options': ['Acceptable', 'ALARP', 'Unacceptable'], 'label': 'Risk Acceptability'},
                {'name': 'risk_benefit', 'format': 'long_text', 'label': 'Risk Benefit'},
            ],
        },
        {
            'code': 'RCM',
            'name': 'Risk Control Measure',
            'prefix': 'RCM-',
            'directory': '10_rcm',
            'icon': '🛡️',
            'page_enabled': True,
            'page_number': 11,
            'properties': [
                'id',
                {'name': 'title', 'format': 'short_text', 'label': 'Title'},
                {'name': 'content', 'format': 'long_text', 'label': 'Content'},
                {'name': 'mitigates', 'format': 'relationship', 'target_types': ['RISK'], 'label': 'Mitigates'},
                {'name': 'implements', 'format': 'relationship', 'target_types': ['SYS'], 'label': 'Implemented By'},
                {'name': 'control_type', 'format': 'select', 'options': ['Inherently Safe Design', 'Protective Measure', 'Information for Safety'], 'label': 'Control Type'},
                {'name': 'implementation_status', 'format': 'select', 'options': ['Planned', 'Implemented'], 'label': 'Implementation Status'},
                {'name': 'verification_status', 'format': 'select', 'options': ['Not Verified', 'Verified'], 'label': 'Verification Status'},
            ],
        },
        {
            'code': 'REL',
            'name': 'Release',
            'prefix': 'REL-',
            'directory': '10_rel',
            'icon': '🚀',
            'page_enabled': True,
            'page_number': 4,
            'properties': [
                'id',
                {'name': 'title', 'format': 'short_text', 'label': 'Title'},
                {'name': 'version', 'format': 'short_text', 'label': 'Version'},
                {'name': 'content', 'format': 'long_text', 'label': 'Content'},
                {'name': 'included_items', 'format': 'item_multiselect', 'target_types': ['CR'], 'label': 'Included Items'},
                {'name': 'release_notes', 'format': 'long_text', 'label': 'Release Notes'},
            ],
            'lifecycle': {
                'transitions': [
                    {'from_states': [None], 'to_state': 'draft'},
                    {'from_states': ['draft'], 'to_state': 'approved',
                     'criteria': [
                         {'id': 'version_set', 'name': 'Version defined',
                          'check_type': 'field_not_empty', 'field': 'version', 'required': True},
                     ], 'label': 'Approve'},
                    {'from_states': ['approved'], 'to_state': 'released', 'label': 'Release'},
                ]
            },
        },
        {
            'code': 'DEF',
            'name': 'Defect',
            'prefix': 'DEF-',
            'directory': '14_def',
            'icon': '🐛',
            'page_enabled': True,
            'page_number': 13,
            'properties': [
                'id',
                {'name': 'title', 'format': 'short_text', 'label': 'Title'},
                {'name': 'description', 'format': 'long_text', 'label': 'Description'},
                {'name': 'severity', 'format': 'select', 'options': ['Critical', 'High', 'Medium', 'Low'], 'label': 'Severity'},
            ],
            'lifecycle': {
                'transitions': [
                    {'from_states': [None], 'to_state': 'draft'},
                    {'from_states': ['draft'], 'to_state': 'open', 'label': 'Submit'},
                    {'from_states': ['open'], 'to_state': 'in_progress', 'label': 'Start Work'},
                    {'from_states': ['in_progress'], 'to_state': 'resolved', 'label': 'Resolve'},
                    {'from_states': ['resolved'], 'to_state': 'closed', 'label': 'Close'},
                    {'from_states': ['open'], 'to_state': 'cancelled', 'label': "Won't Fix"},
                ]
            },
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

    print(f"[OK] Created split config: global.yaml + {len(doc_type_configs)} doc_types/*.yaml")

    # Create directory structure for document types
    doc_type_dirs = [
        "00_uc", "01_req_crs", "02_req_sys", "03_req_srs",
        "04_req_sds", "05_swdd", "06_swad", "07_sysarch",
        "08_cr", "09_risk", "10_rcm", "10_rel", "11_tc", "14_def",
    ]

    items_dir = test_dir / "items"
    items_dir.mkdir(parents=True)

    for doc_dir in doc_type_dirs:
        (items_dir / doc_dir).mkdir(parents=True, exist_ok=True)

    (test_dir / "documents" / "specifications" / "templates").mkdir(parents=True)
    (test_dir / "documents" / "plans").mkdir(parents=True)
    (test_dir.parent / "governance").mkdir(parents=True)

    # Create a test document for document_content checks
    test_plan = test_dir / "documents" / "plans" / "test_plan.md"
    test_plan.write_text(
        "# Test Plan\n\nThis document describes testing and verification procedures.\n",
        encoding="utf-8",
    )

    print(f"[OK] Created directory structure for {len(doc_type_dirs)} document types")

    return test_dir


def get_test_dataset() -> List[Dict]:
    """
    Get minimal test dataset for API tests.

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
        # Approved CR with implementation PRs — used by cr_git_evidence and CR CLI tests
        {
            'id': 'CR-002',
            'title': 'Approved Change Request with PR',
            'description': 'Change request that has been approved and has linked PRs',
            'justification': 'Demonstrates CR-git-evidence policy check',
            'status': 'approved',
            'affected_items': ['SYS-001'],
            'implementation_prs': ['https://github.com/org/repo/pull/42'],
        },
        # Defects — closed/resolved ones should not block; draft ones are ignored
        {
            'id': 'DEF-001',
            'title': 'Closed High Defect',
            'description': 'A high-severity defect that has been resolved and closed.',
            'severity': 'High',
            'status': 'closed',
        },
        {
            'id': 'DEF-002',
            'title': 'Closed Low Defect',
            'description': 'A low-severity defect that has been closed.',
            'severity': 'Low',
            'status': 'closed',
        },
    ]


def populate_governance(test_dhf_root: Path):
    """Create governance directory with IEC 62304 test policies."""
    governance_dir = test_dhf_root.parent / "governance"
    governance_dir.mkdir(parents=True, exist_ok=True)

    iec_62304_policy = {
        'id': 'IEC_62304',
        'title': 'IEC 62304 Medical Device Software',
        'type': 'standard',
        'version': '2015',
        'policies': [
            {
                'id': '5.1.1',
                'section': '5.1.1',
                'text': 'All software requirements shall be traceable to system requirements',
                'status': 'approved'
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
            },
            {
                'id': 'TEST.doc_content',
                'section': 'TEST',
                'text': 'A test plan document shall describe testing procedures',
                'status': 'approved',
                'automation': {
                    'check': 'document_content',
                    'params': {
                        'doc_id': 'test_plan',
                        'keywords': ['testing', 'verification'],
                    }
                }
            },
            {
                'id': 'TEST.attr_value',
                'section': 'TEST',
                'text': 'SRS items shall derive from SYS',
                'status': 'approved',
                'automation': {
                    'check': 'attribute_value',
                    'params': {
                        'type_code': 'SRS',
                        'attribute': 'title',
                        'expected_value': 'Item Persistence and Versioning',
                    }
                }
            },
            {
                'id': 'TEST.no_open_defects',
                'section': 'TEST',
                'text': 'No Critical or High severity defects shall be open at release.',
                'status': 'approved',
                'automation': {
                    'check': 'no_open_defects',
                    'params': {
                        'severity_threshold': ['Critical', 'High'],
                    }
                }
            },
        ]
    }

    with open(governance_dir / "IEC_62304.yaml", 'w') as f:
        yaml.dump(iec_62304_policy, f, default_flow_style=False, sort_keys=False)

    print(f"[OK] Created governance policies: IEC_62304.yaml with {len(iec_62304_policy['policies'])} policies")

    iso_14971_policy = {
        'id': 'ISO_14971',
        'title': 'ISO 14971 Risk Management',
        'type': 'standard',
        'version': '2019',
        'policies': [
            {
                'id': '7.2.a',
                'section': '7.2',
                'text': 'Risk control measures shall be implemented.',
                'status': 'approved',
                'automation': {
                    'check': 'attribute_value',
                    'params': {
                        'type_code': 'RCM',
                        'attribute': 'implementation_status',
                        'expected_value': 'Implemented',
                    },
                },
            },
            {
                'id': '7.6.b',
                'section': '7.6',
                'text': 'Risk control measures shall be verified as effective.',
                'status': 'approved',
                'automation': {
                    'check': 'attribute_value',
                    'params': {
                        'type_code': 'RCM',
                        'attribute': 'verification_status',
                        'expected_value': 'Verified',
                    },
                },
            },
        ],
    }

    with open(governance_dir / "ISO_14971.yaml", 'w') as f:
        yaml.dump(iso_14971_policy, f, default_flow_style=False, sort_keys=False)

    print(f"[OK] Created governance policies: ISO_14971.yaml with {len(iso_14971_policy['policies'])} policies")


def populate_test_dhf(test_dhf_root: Path):
    """
    Populate test DHF with minimal dataset.

    Uses ItemSaver directly so that hardcoded IDs in test fixtures are preserved.
    IDs must remain stable because test items cross-reference each other by ID.

    Returns:
        None
    """
    from utils.models.config import ProjectConfig
    from utils.models.item import Item
    from utils.repository.saver import ItemSaver
    from utils.local_adapter import LocalDHFAdapter

    print(f"\n[DATA] Populating test DHF with test data...")

    populate_governance(test_dhf_root)

    config = ProjectConfig.load(test_dhf_root / "config")
    saver = ItemSaver(test_dhf_root / "items", git_repo=None, project_config=config)

    test_items = get_test_dataset()
    for item_data in test_items:
        try:
            item = Item.model_validate(item_data)
            saver.save(item)
            print(f"  [OK] Created {item_data['id']}")
        except Exception as e:
            print(f"  [WARN] Failed to create {item_data['id']}: {e}")
            import traceback
            traceback.print_exc()

    # Transition CR-002 to 'approved' so CR CLI tests and cr_git_evidence checks
    # can test the approved-CR happy path.
    adapter = LocalDHFAdapter(test_dhf_root, auto_commit=False)
    try:
        adapter.execute_transition("CR-002", "approved", performed_by="test-setup")
        print("  [OK] Transitioned CR-002 → approved")
    except Exception as e:
        print(f"  [WARN] Could not approve CR-002: {e}")

    print(f"[OK] Test DHF populated with {len(test_items)} items")
