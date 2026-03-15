"""
Pytest configuration and fixtures for API tests.
"""

import pytest
import sys
import shutil
from pathlib import Path

# Add parent directory to path so we can import from tests.fixtures
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import shared test data fixtures
from fixtures.test_data import create_test_dhf, populate_test_dhf


@pytest.fixture(scope="function")
def test_dhf_root():
    """
    Create isolated test DHF directory for API tests.

    This fixture creates a temporary DHF with test data for each test function.
    Using function scope ensures each test has a clean, isolated environment.
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
