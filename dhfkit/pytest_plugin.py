"""pytest plugin — DHF traceability markers for JUnit XML output.

Usage:
    @pytest.mark.dhf_links("SRS-001", "SYS-004")
    def test_something():
        ...

    @pytest.mark.dhf_id("TC-SYS-001")
    @pytest.mark.dhf_links("SYS-001")
    def test_explicit_id():
        ...

When pytest is run with --junit-xml, each marked test case gets:
  <property name="medharness.links" value="SRS-001,SYS-004"/>
  <property name="medharness.id"    value="TC-SYS-001"/>

These properties are read by `ci test-coverage` to determine requirement coverage.
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


@pytest.fixture(autouse=True)
def _dhf_junit_properties(request: pytest.FixtureRequest, record_property: Callable[[str, object], None]) -> None:
    links_marker = request.node.get_closest_marker("dhf_links")
    if links_marker:
        record_property("medharness.links", ",".join(str(a) for a in links_marker.args))

    id_marker = request.node.get_closest_marker("dhf_id")
    if id_marker and id_marker.args:
        record_property("medharness.id", str(id_marker.args[0]))
