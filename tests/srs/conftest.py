```
"""Shared fixtures for user workflow tests."""
import pytest
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# Import shared test data creation
from tests.fixtures.test_data import create_test_dhf
from traceability.compliant_flow_core import CompliantFlowCore


@pytest.fixture
def test_dhf():
    """Create minimal test DHF structure - uses shared test_data module."""
    return create_test_dhf()


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
