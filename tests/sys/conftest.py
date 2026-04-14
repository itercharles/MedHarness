"""
Pytest configuration and fixtures for SYS API tests.
"""

import pytest
import sys
from pathlib import Path

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
