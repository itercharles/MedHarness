"""A test that failed is not evidence: `verify completion` does not close a requirement on it."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from dhfkit.tests.fixtures import bare_dhf
from medharness.services.verify_completion import cr_closure_gate


def _closed_over_srs_010(tmp_path: Path) -> Path:
    dhf = tmp_path / "DHF"
    bare_dhf(dhf)
    (dhf / "items" / "07_cr").mkdir(parents=True, exist_ok=True)
    (dhf / "items" / "07_cr" / "CR-001.yaml").write_text(
        "id: CR-001\ntitle: CR\nimplementation_notes: plan\naffected_risk_items: []\naffected_items: [SRS-010]\n")
    (dhf / "items" / "03_srs" / "SRS-010.yaml").write_text(
        "id: SRS-010\ntitle: Requirement\nstatus: draft\nverification_method: [Test]\n")
    return dhf


@pytest.mark.dhf_links("SRS-005")


@pytest.mark.dhf_testing("T3")


@pytest.mark.dhf_links("SRS-005")
@pytest.mark.dhf_testing("T3")
def test_the_only_test_linked_to_the_item_failed(tmp_path: Path) -> None:
    dhf = _closed_over_srs_010(tmp_path)
    suite = ET.Element("testsuite")
    case = ET.SubElement(suite, "testcase", name="test_it", classname="Tests")
    ET.SubElement(ET.SubElement(case, "properties"), "property", name="medharness.links", value="SRS-010")
    ET.SubElement(case, "failure", message="assertion failed")
    junit = tmp_path / "results.xml"
    ET.ElementTree(suite).write(str(junit))

    result = cr_closure_gate("CR-001", dhf, junit_paths=(junit,))

    assert result["passed"] is False
    assert "SRS-010" in [i["id"] for i in result["details"]["unverified_test"]]
