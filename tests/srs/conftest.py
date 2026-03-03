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
    # Includes: UC-001, CRS-001, SYS-001, SYS-002, SRS-001, SRS-002, SYSARCH-001, CR-001
    # Requirement items (UC/CRS/SYS/SRS/SYSARCH) have no status (GitOps model)
    # CR-001 has status: draft (explicit lifecycle)
    core = populate_test_dhf(test_dhf)
    return core


