"""
Shared test data fixtures for API tests.

Provides a pre-populated StubDHFAdapter and governance directory helpers
for both CRS and SYS tests.
"""

from pathlib import Path
from typing import Dict, List


def get_test_dataset() -> List[Dict]:
    """
    Get minimal test dataset for API tests.

    Returns complete traceability chain and supporting items.
    """
    from tests.fixtures.shared_test_data import get_common_test_dataset

    items = get_common_test_dataset()

    # Extended items only needed by medharness API tests
    items.extend([
        {
            'id': 'CR-002',
            'title': 'Approved Change Request with PR',
            'description': 'Change request that has been approved and has linked PRs',
            'justification': 'Demonstrates CR-git-evidence policy check',
            'status': 'approved',
            'affected_items': ['SYS-001'],
            'implementation_prs': ['https://github.com/org/repo/pull/42'],
        },
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
    ])

    return items


def build_test_adapter():
    """
    Build a StubDHFAdapter pre-populated with the standard test dataset.

    Returns a fully configured in-memory adapter ready for use as a
    MedHarnessCore backing store. IDs are stable and cross-reference
    each other.
    """
    from tests.fixtures.stub_adapter import StubDHFAdapter

    adapter = StubDHFAdapter()
    for item in get_test_dataset():
        _add_all_linked_uids(item)
        adapter._items[item['id']] = item

    # Standard test document for document_content checks
    adapter._documents['test_plan'] = (
        "# Test Plan\n\nThis document describes testing and verification procedures.\n"
    )

    return adapter


def _add_all_linked_uids(item: dict) -> None:
    _LINK_FIELDS = ("derives_from", "implements", "mitigates", "satisfies", "guided_by", "informs", "design", "verifies", "validates")
    linked = []
    for field in _LINK_FIELDS:
        vals = item.get(field)
        if isinstance(vals, list):
            linked.extend(vals)
    item["all_linked_uids"] = linked

def populate_governance(governance_dir: Path) -> None:
    """Create governance directory with IEC 62304 and ISO 14971 test policies."""
    import yaml

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
