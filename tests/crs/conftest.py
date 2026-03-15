"""
Pytest configuration and fixtures for CRS API tests.
"""
import sys
import shutil
from pathlib import Path

import pytest

# Add parent directory to path so we can import from tests.fixtures
sys.path.insert(0, str(Path(__file__).parent.parent))

from fixtures.test_data import create_test_dhf, populate_test_dhf


@pytest.fixture(scope="function")
def test_dhf_root():
    """
    Create isolated test DHF directory for CRS API tests.

    Each test function gets a clean, isolated environment.
    """
    test_dir = create_test_dhf()
    populate_test_dhf(test_dir)

    yield test_dir

    # Cleanup (remove project root, which contains DHF/ and governance/ siblings)
    project_root = test_dir.parent
    if project_root.exists():
        shutil.rmtree(project_root)


@pytest.fixture(scope="function")
def governance_dir(test_dhf_root):
    """Return the governance directory for the test DHF."""
    return test_dhf_root.parent / "governance"


@pytest.fixture(scope="function")
def core(test_dhf_root):
    """Return a CompliantFlowCore instance backed by the test DHF."""
    from utils.local_adapter import LocalDHFAdapter
    from compliantflow.core import CompliantFlowCore
    adapter = LocalDHFAdapter(test_dhf_root, auto_commit=False)
    return CompliantFlowCore(adapter)
