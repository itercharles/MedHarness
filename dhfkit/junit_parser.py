"""JUnit XML reader: which tests exist, whether they passed, and what they claim to verify.

A test claims an item with the ``medharness.links`` property (comma-separated IDs) or an
``@links:SRS-011`` tag in its name, and a numbered test point with ``medharness.testing``
or ``@testing:T1``. The pytest plugin (``dhfkit.pytest_plugin``) writes the properties from
markers; other frameworks put the tags in the test name.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List

# Stable JUnit XML property names: downstream reporters write these.
JUNIT_LINKS = "medharness.links"
JUNIT_TESTING = "medharness.testing"

# @links:SRS-011 and @testing:T1 embedded in a test name (JS and other non-pytest frameworks).
LINKS_TAG_RE = re.compile(r"@links:([\w-]+)")
TESTING_TAG_RE = re.compile(r"@testing:(T\d+)")


def _parse_properties(testcase: ET.Element) -> dict:
    """Extract <property> elements inside a <testcase> into a dict."""
    props: dict = {}
    properties_el = testcase.find("properties")
    if properties_el is not None:
        for prop in properties_el.findall("property"):
            name = prop.get("name", "")
            value = prop.get("value", "")
            if name:
                props[name] = value
    return props


@dataclass
class TestEvidence:
    """One test case as evidence for the items it links to."""

    __test__ = False      # not a pytest test class

    name: str
    suite: str
    status: str                                              # PASS / FAIL / SKIP
    links: List[str] = field(default_factory=list)           # item IDs it verifies
    testing_points: List[str] = field(default_factory=list)  # test points it covers


def read_test_evidence(paths: Iterable[Path]) -> List[TestEvidence]:
    """Every test case in the JUnit files, with the items and test points it links to.

    A link is the `medharness.links` property or an `@links:ID` tag in the test name,
    and a test point is `medharness.testing` or `@testing:T1`: one reader, so no check
    sees a test another does not. No TC ID is needed, unlike `parse_junit_xml`.
    """
    evidence: List[TestEvidence] = []
    for path in paths:
        if not Path(path).is_file():
            continue
        for testcase in ET.parse(path).getroot().iter("testcase"):
            name = testcase.get("name", "")
            props = _parse_properties(testcase)
            links = [v.strip() for v in props.get(JUNIT_LINKS, "").split(",") if v.strip()]
            points = [v.strip() for v in props.get(JUNIT_TESTING, "").split(",") if v.strip()]
            if testcase.find("failure") is not None or testcase.find("error") is not None:
                status = "FAIL"
            elif testcase.find("skipped") is not None:
                status = "SKIP"
            else:
                status = "PASS"
            evidence.append(TestEvidence(
                name=name, suite=testcase.get("classname", ""), status=status,
                links=list(dict.fromkeys(links + LINKS_TAG_RE.findall(name))),
                testing_points=list(dict.fromkeys(points + TESTING_TAG_RE.findall(name))),
            ))
    return evidence
