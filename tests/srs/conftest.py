"""Shared fixtures for SRS workflow tests."""
import pytest
from pathlib import Path
import sys

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import shared test data creation
from tests.fixtures.test_data import create_test_dhf, populate_test_dhf
from compliantflow.core import CompliantFlowCore


@pytest.fixture
def test_dhf():
    """Create minimal test DHF structure - uses shared test_data module."""
    return create_test_dhf()


@pytest.fixture
def test_core(test_dhf):
    """Initialize CompliantFlowCore with test DHF and populate with test data."""
    # Populate test DHF with standard test dataset
    # Includes: UC-001, CRS-001, SYS-001 (approved), SYS-002 (draft), 
    #           SRS-001, SRS-002, SYSARCH-001, CR-001
    core = populate_test_dhf(test_dhf)
    return core


@pytest.fixture
def draft_sys_item(test_core):
    """
    Get the draft SYS-002 item from test dataset.
    
    Note: SYS-002 is already created by populate_test_dhf as a draft item
    """
    return test_core.get_item('SYS-002')


@pytest.fixture
def approved_sys_item(test_core):
    """
    Get the approved SYS-001 item from test dataset.
    
    Note: SYS-001 is already created by populate_test_dhf as an approved item
    """
    return test_core.get_item('SYS-001')
