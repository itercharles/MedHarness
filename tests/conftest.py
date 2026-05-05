"""Root conftest — shared fixtures for unit and integration tests.

Previously this injected medharness.* JUnit XML properties from
docstring @links / @test_id tags. That has been removed because the
tool repo no longer governs itself through DHF requirement traceability.

User projects that want requirement-linked JUnit evidence should use
the medharness test framework guidance in their own repos.
"""

import sys
from pathlib import Path

import pytest

# Make tests/ root importable for shared fixtures
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fixtures.data import build_test_adapter, populate_governance


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
