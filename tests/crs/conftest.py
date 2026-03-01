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

    if test_dir.exists():
        shutil.rmtree(test_dir)


@pytest.fixture(scope="function")
def core(test_dhf_root):
    """Return a CompliantFlowCore instance backed by the test DHF."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
    from traceability.compliant_flow_core import CompliantFlowCore
    return CompliantFlowCore(test_dhf_root, auto_commit=False)
