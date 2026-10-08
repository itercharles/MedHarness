"""Tests for dhfkit.pytest_plugin — JUnit XML property injection."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest


pytest_plugins = ["pytester"]


@pytest.fixture(autouse=True)
def _ensure_plugin_loaded(pytester: pytest.Pytester) -> None:
    """Load the plugin in the inner pytest session, guarding against double-registration.

    In CI the package is installed with a pytest11 entry point (name='dhfkit'), so the
    plugin is already active. Locally (source-only, no editable install) it isn't, so we
    import it explicitly.  The has_plugin guard prevents the ValueError that pluggy raises
    when the same module is registered under two different names.
    """
    pytester.makeconftest("""
def pytest_configure(config):
    pm = config.pluginmanager
    if not pm.has_plugin('dhfkit') and not pm.has_plugin('dhfkit.pytest_plugin'):
        pm.import_plugin('dhfkit.pytest_plugin')
""")


def _properties(junit_xml: Path, test_name_substr: str) -> dict[str, str]:
    """Parse JUnit XML and return properties dict for the matching testcase."""
    tree = ET.parse(junit_xml)
    for tc in tree.iter("testcase"):
        if test_name_substr in tc.get("name", ""):
            props = tc.find("properties")
            if props is None:
                return {}
            return {p.get("name"): p.get("value") for p in props.findall("property")}
    raise AssertionError(f"No testcase matching {test_name_substr!r} in {junit_xml}")


def test_dhf_links_marker_injects_links_property(pytester: pytest.Pytester) -> None:
    pytester.makepyfile("""
        import pytest

        @pytest.mark.dhf_links("SRS-001", "SYS-004")
        def test_example():
            pass
    """)
    xml = pytester.path / "result.xml"
    result = pytester.runpytest(f"--junit-xml={xml}")
    result.assert_outcomes(passed=1)

    props = _properties(xml, "test_example")
    assert props.get("medharness.links") == "SRS-001,SYS-004"


def test_links_and_testing_markers_combine(pytester: pytest.Pytester) -> None:
    pytester.makepyfile("""
        import pytest

        @pytest.mark.dhf_testing("T1", "T2")
        @pytest.mark.dhf_links("SRS-007", "SYS-002")
        def test_full():
            pass
    """)
    xml = pytester.path / "result.xml"
    pytester.runpytest(f"--junit-xml={xml}")

    props = _properties(xml, "test_full")
    assert props == {"medharness.links": "SRS-007,SYS-002", "medharness.testing": "T1,T2"}


def test_unmarked_test_has_no_dhf_properties(pytester: pytest.Pytester) -> None:
    pytester.makepyfile("""
        def test_plain():
            pass
    """)
    xml = pytester.path / "result.xml"
    pytester.runpytest(f"--junit-xml={xml}")

    props = _properties(xml, "test_plain")
    assert props == {}


def test_markers_registered_no_unknown_warning(pytester: pytest.Pytester) -> None:
    pytester.makepyfile("""
        import pytest

        @pytest.mark.dhf_links("SRS-001")
        def test_no_warning():
            pass
    """)
    result = pytester.runpytest("-W", "error::pytest.PytestUnknownMarkWarning")
    result.assert_outcomes(passed=1)


def test_single_dhf_link(pytester: pytest.Pytester) -> None:
    pytester.makepyfile("""
        import pytest

        @pytest.mark.dhf_links("SRS-001")
        def test_one():
            pass
    """)
    xml = pytester.path / "result.xml"
    pytester.runpytest(f"--junit-xml={xml}")

    props = _properties(xml, "test_one")
    assert props.get("medharness.links") == "SRS-001"
