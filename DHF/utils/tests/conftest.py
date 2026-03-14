"""Shared fixtures for DHF utility tests."""
import pytest
from pathlib import Path
import sys

# Add project root to sys.path so utils.* and compliantflow.* resolve correctly
# DHF/utils/tests/ → parent.parent.parent = project root
_project_root = Path(__file__).parent.parent.parent.parent
if str(_project_root / "src") not in sys.path:
    sys.path.insert(0, str(_project_root / "src"))
if str(_project_root / "DHF") not in sys.path:
    sys.path.insert(0, str(_project_root / "DHF"))

from utils.tests.fixtures import create_test_dhf, populate_test_dhf_direct


@pytest.fixture
def test_dhf():
    """Create minimal isolated test DHF directory."""
    return create_test_dhf()


@pytest.fixture
def test_core(test_dhf):
    """
    CompliantFlowCore instance with test DHF populated via ItemSaver.

    Data is written directly (no core dependency at setup time).
    Returns a CompliantFlowCore for tests that need to call core API methods.
    """
    populate_test_dhf_direct(test_dhf)

    from utils.local_adapter import LocalDHFAdapter
    from compliantflow.core import CompliantFlowCore
    adapter = LocalDHFAdapter(test_dhf, auto_commit=False)
    return CompliantFlowCore(adapter)


@pytest.fixture
def loader(test_dhf, test_core):
    """
    ItemLoader for direct DHF-layer testing.

    DHF utility tests MAY import utils.* directly (they test the DHF layer).
    This fixture provides ItemLoader using the populated test DHF.
    """
    from utils.repository.loader import ItemLoader
    return ItemLoader(test_dhf / "items", project_config=test_core.config)
