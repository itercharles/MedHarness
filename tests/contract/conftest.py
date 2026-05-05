"""Contract test fixtures: scaffold a DHF from templates for integration tests."""

import tempfile
from pathlib import Path

import pytest

from medharness.workflows.init import _scaffold_dhf, _replace_placeholders


@pytest.fixture(scope="module")
def scaffolded_dhf():
    """Scaffold a temp DHF repo from templates — the integration test target."""
    with tempfile.TemporaryDirectory() as tmp:
        dhf_dir = Path(tmp) / "starter-dhf"
        _scaffold_dhf(dhf_dir)
        _replace_placeholders(dhf_dir, "Test Project")
        yield dhf_dir
