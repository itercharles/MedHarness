"""Shared fixtures for dhfkit CLI tests."""
import pytest
from pathlib import Path
import sys

# Add project root to sys.path so dhfkit is importable
# dhfkit/tests/ -> parent.parent = project root
_project_root = Path(__file__).parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from dhfkit.tests.fixtures import create_test_dhf, populate_test_dhf_direct


@pytest.fixture
def populated_dhf():
    """Populated test DHF directory as Path. Used by all CLI tests via --dhf."""
    root = create_test_dhf()
    populate_test_dhf_direct(root)
    return root
