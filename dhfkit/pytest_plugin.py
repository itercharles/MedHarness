"""pytest plugin — DHF traceability markers for JUnit XML output.

Usage:
    @pytest.mark.dhf_links("SRS-001", "SYS-004")
    def test_something():
        ...

    @pytest.mark.dhf_id("TC-SYS-001")
    @pytest.mark.dhf_links("SYS-001")
    def test_explicit_id():
        ...

    @pytest.mark.dhf_testing("T1", "T2")
    @pytest.mark.dhf_links("SRS-011")
    def test_numbered_points():
        ...

When pytest is run with --junit-xml, each marked test case gets:
  <property name="medharness.links"   value="SRS-001,SYS-004"/>
  <property name="medharness.id"      value="TC-SYS-001"/>
  <property name="medharness.testing" value="T1,T2"/>

These properties are read by `verify tests` to determine requirement
coverage and, when requirements define numbered test points, test-point
coverage as well.
"""

from __future__ import annotations

from typing import Callable

import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "dhf_links(*ids): link test to DHF requirement IDs "
        "(writes medharness.links property to JUnit XML output)",
    )
    config.addinivalue_line(
        "markers",
        "dhf_id(id): set explicit TC ID for this test "
        "(writes medharness.id property to JUnit XML output)",
    )
    config.addinivalue_line(
        "markers",
        "dhf_testing(*points): declare numbered test-point IDs covered by this test "
        "(writes medharness.testing property to JUnit XML output, e.g. 'T1,T2')",
    )


@pytest.fixture(autouse=True)
def _dhf_junit_properties(request: pytest.FixtureRequest, record_property: Callable[[str, object], None]) -> None:
    links_marker = request.node.get_closest_marker("dhf_links")
    id_marker = request.node.get_closest_marker("dhf_id")
    testing_marker = request.node.get_closest_marker("dhf_testing")

    if links_marker:
        record_property("medharness.links", ",".join(str(a) for a in links_marker.args))

    if id_marker and id_marker.args:
        record_property("medharness.id", str(id_marker.args[0]))
    elif links_marker and links_marker.args:
        # Auto-derive TC ID from the first linked requirement so parse_junit_xml
        # picks up the result for evidence ingestion without requiring dhf_id.
        # Use explicit @pytest.mark.dhf_id when multiple tests cover the same requirement.
        record_property("medharness.id", f"TC-{links_marker.args[0]}")

    if testing_marker:
        record_property("medharness.testing", ",".join(str(a) for a in testing_marker.args))
