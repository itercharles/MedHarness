"""
Shared test items used by both medharness unit tests and dhfkit tests.

Previously these 8 items were copy-pasted identically between
tests/fixtures/data.py and dhfkit/tests/fixtures.py.
"""

from typing import Dict, List


def get_common_test_dataset() -> List[Dict]:
    return [
        {"id": "UC-001", "title": "User Need - Test Item", "content": "User needs test functionality"},
        {
            "id": "CRS-001",
            "title": "Customer Requirement - Test Item",
            "content": "Customer requires test feature",
            "derives_from": ["UC-001"],
        },
        {
            "id": "SYS-001",
            "title": "System Requirement - Test Item",
            "content": "System shall provide test capability",
            "derives_from": ["CRS-001"],
        },
        {
            "id": "SYS-002",
            "title": "Draft System Requirement",
            "content": "System shall perform function X",
            "category": "Functional",
            "derives_from": ["CRS-001"],
        },
        {
            "id": "SRS-001",
            "title": "Item Persistence and Versioning",
            "content": "Software shall persist items to YAML files with version control",
            "derives_from": ["SYS-001"],
        },
        {
            "id": "SRS-002",
            "title": "Graph-based Traceability",
            "content": "Software shall provide graph-based traceability visualization",
            "derives_from": ["SYS-001"],
        },
        {
            "id": "SYSARCH-001",
            "title": "System Architecture Component",
            "content": "Architecture component for test system",
            "implements": ["SYS-001"],
        },
        {
            "id": "CR-001",
            "title": "Test Change Request",
            "description": "Change request for testing purposes",
            "justification": "Testing CR workflow",
            "status": "draft",
            "affected_items": ["SRS-001"],
        },
    ]
