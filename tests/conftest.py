"""Root conftest — shared fixtures for unit and integration tests.

MedHarness keeps its own DHF (`DHF/`, see docs/validation.md). A test that verifies
one of its requirements carries `@pytest.mark.dhf_links("SRS-nnn")` and, for a numbered
test point, `@pytest.mark.dhf_testing("Tn")`. The `dhfkit` pytest plugin turns those into
`medharness.links` and `medharness.testing` properties in the JUnit XML, which
`medharness verify tests` reads. The plugin is the package's `pytest11` entry point;
`pytest_configure` below loads it when the package is not installed.
"""

import sys
from pathlib import Path

import pytest

# Make tests/ root importable for shared fixtures
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fixtures.data import build_test_adapter, populate_governance


def pytest_configure(config):
    pm = config.pluginmanager
    if not pm.has_plugin("dhfkit") and not pm.has_plugin("dhfkit.pytest_plugin"):
        pm.import_plugin("dhfkit.pytest_plugin")


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
def populated_dhf():
    """The dhfkit test DHF, populated, for command tests that pass it as --dhf."""
    from dhfkit.tests.fixtures import create_test_dhf, populate_test_dhf_direct

    root = create_test_dhf()
    populate_test_dhf_direct(root)
    return root
