"""
Pytest configuration and fixtures for CRS API tests.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from fixtures.test_data import build_test_adapter, populate_governance


@pytest.fixture
def stub_adapter():
    """In-memory DHF adapter pre-populated with the standard test dataset."""
    return build_test_adapter()


@pytest.fixture
def governance_dir(tmp_path):
    """Temporary governance directory populated with IEC 62304 and ISO 14971 policies."""
    gov_dir = tmp_path / "governance"
    populate_governance(gov_dir)
    return gov_dir


@pytest.fixture
def core(stub_adapter):
    """Return a CompliantFlowCore instance backed by the in-memory stub adapter."""
    from compliantflow.core import CompliantFlowCore
    return CompliantFlowCore(stub_adapter)
