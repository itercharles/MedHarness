"""Shared fixtures for DHF utility CLI tests."""
import pytest
from pathlib import Path
import sys

# Add project root to sys.path so utils.* and compliantflow.* resolve correctly
# DHF/utils/tests/ → parent.parent.parent.parent = project root
_project_root = Path(__file__).parent.parent.parent.parent
if str(_project_root / "src") not in sys.path:
    sys.path.insert(0, str(_project_root / "src"))
if str(_project_root / "DHF") not in sys.path:
    sys.path.insert(0, str(_project_root / "DHF"))

from utils.tests.fixtures import create_test_dhf, populate_test_dhf_direct


@pytest.fixture
def populated_dhf():
    """Populated test DHF directory as Path. Used by all CLI tests via --dhf."""
    root = create_test_dhf()
    populate_test_dhf_direct(root)
    return root
