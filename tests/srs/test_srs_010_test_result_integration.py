"""Tests for SRS-010: Test Result Integration

Verifies the new docstring-based metadata injection mechanism:
  - pytest conftest extracts @-tags from docstrings
  - junit_parser correctly parses compliantflow.* properties
  - ResultStore persists all fields correctly

@links: SRS-010
"""

import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))

from utils.junit_parser import parse_junit_xml
from utils.result_store import ResultStore
from docstring_parser import parse_docstring, extract_tc_id_from_name


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_junit_xml(path: Path, testcases: list[dict]) -> None:
    """Write a minimal JUnit XML file."""
    root = ET.Element("testsuites")
    suite = ET.SubElement(root, "testsuite", name="suite")
    for tc in testcases:
        case = ET.SubElement(suite, "testcase", name=tc["name"], time="0.1")
        if tc.get("props"):
            props_el = ET.SubElement(case, "properties")
            for k, v in tc["props"].items():
                ET.SubElement(props_el, "property", name=k, value=v)
        if tc.get("failure"):
            ET.SubElement(case, "failure", message=tc["failure"])
        if tc.get("skipped"):
            ET.SubElement(case, "skipped")
    path.write_text(ET.tostring(root, encoding="unicode"))


# ---------------------------------------------------------------------------
# TC-SRS-010-001: conftest _parse_docstring extracts all tags
# ---------------------------------------------------------------------------

def test_TC_SRS_010_001_parse_docstring_extracts_all_tags():
    """
    TC-SRS-010-001: _parse_docstring extracts title and all @-tags.

    @test_id: TC-SRS-010-001
    @links: SRS-010
    """
    doc = """
    TC-SYS-001-001: My test title

    @test_id: TC-SYS-001-001
    @links: SYS-001, SYS-002
    @reviewer: Alice
    @review_status: approved
    @review_date: 2026-01-15
    """
    meta = parse_docstring(doc)

    assert meta["title"] == "My test title"
    assert meta["test_id"] == "TC-SYS-001-001"
    assert meta["links"] == "SYS-001, SYS-002"
    assert meta["reviewer"] == "Alice"
    assert meta["review_status"] == "approved"
    assert meta["review_date"] == "2026-01-15"


# ---------------------------------------------------------------------------
# TC-SRS-010-002: conftest _extract_tc_id_from_name handles name patterns
# ---------------------------------------------------------------------------

def test_TC_SRS_010_002_extract_tc_id_from_function_name():
    """
    TC-SRS-010-002: _extract_tc_id_from_name handles various naming patterns.

    @test_id: TC-SRS-010-002
    @links: SRS-010
    """
    cases = [
        ("test_TC_SYS_001_001_my_test",   "TC-SYS-001-001"),
        ("test_TC_CRS_008_002_something",  "TC-CRS-008-002"),
        ("test_TC_SRS_010_001_foo",        "TC-SRS-010-001"),
        ("test_TC_SYS_033_pass",           "TC-SYS-033"),
        ("test_without_tc_id",             None),
    ]
    for name, expected in cases:
        result = extract_tc_id_from_name(name)
        assert result == expected, f"{name!r} → expected {expected!r}, got {result!r}"


# ---------------------------------------------------------------------------
# TC-SRS-010-003: junit_parser extracts id from compliantflow.id property
# ---------------------------------------------------------------------------

def test_TC_SRS_010_003_parse_explicit_id_property():
    """
    TC-SRS-010-003: parse_junit_xml uses compliantflow.id property when present.

    @test_id: TC-SRS-010-003
    @links: SRS-010
    """
    with tempfile.TemporaryDirectory() as tmp:
        xml_path = Path(tmp) / "results.xml"
        _write_junit_xml(xml_path, [{
            "name": "some_generic_test_name",
            "props": {
                "compliantflow.id": "TC-CRS-999",
                "compliantflow.links": "CRS-001",
                "compliantflow.title": "Explicit title",
            },
        }])
        results = parse_junit_xml(xml_path)

    assert len(results) == 1
    assert results[0].id == "TC-CRS-999"
    assert results[0].links == ["CRS-001"]
    assert results[0].title == "Explicit title"
    assert results[0].testing_status == "PASS"


# ---------------------------------------------------------------------------
# TC-SRS-010-004: junit_parser extracts id from test name regex
# ---------------------------------------------------------------------------

def test_TC_SRS_010_004_parse_id_from_test_name():
    """
    TC-SRS-010-004: parse_junit_xml falls back to regex extraction from name.

    @test_id: TC-SRS-010-004
    @links: SRS-010
    """
    with tempfile.TemporaryDirectory() as tmp:
        xml_path = Path(tmp) / "results.xml"
        _write_junit_xml(xml_path, [
            {"name": "test_TC_SYS_001_001_object_creation"},
            {"name": "test_TC_SRS_010_002_foo", "failure": "AssertionError"},
            {"name": "test_TC_CRS_008_001_bar", "skipped": True},
            {"name": "test_no_tc_id"},
        ])
        results = parse_junit_xml(xml_path)

    assert len(results) == 3
    ids = {r.id: r for r in results}
    assert ids["TC-SYS-001-001"].testing_status == "PASS"
    assert ids["TC-SRS-010-002"].testing_status == "FAIL"
    assert ids["TC-CRS-008-001"].testing_status == "SKIP"


# ---------------------------------------------------------------------------
# TC-SRS-010-005: junit_parser extracts review metadata properties
# ---------------------------------------------------------------------------

def test_TC_SRS_010_005_parse_review_metadata_properties():
    """
    TC-SRS-010-005: parse_junit_xml extracts compliantflow.reviewer,
    review_date, review_status from XML properties.

    @test_id: TC-SRS-010-005
    @links: SRS-010
    """
    with tempfile.TemporaryDirectory() as tmp:
        xml_path = Path(tmp) / "results.xml"
        _write_junit_xml(xml_path, [{
            "name": "test_TC_SYS_001_reviewed",
            "props": {
                "compliantflow.reviewer": "Alice",
                "compliantflow.review_date": "2026-01-15",
                "compliantflow.review_status": "approved",
            },
        }])
        results = parse_junit_xml(xml_path)

    assert len(results) == 1
    r = results[0]
    assert r.reviewer == "Alice"
    assert r.review_date == "2026-01-15"
    assert r.review_status == "approved"


# ---------------------------------------------------------------------------
# TC-SRS-010-006: ResultStore persists all fields from record_execution
# ---------------------------------------------------------------------------

def test_TC_SRS_010_006_result_store_persists_all_fields():
    """
    TC-SRS-010-006: ResultStore.record_execution stores execution and
    review fields together in results.yaml.

    @test_id: TC-SRS-010-006
    @links: SRS-010
    """
    with tempfile.TemporaryDirectory() as tmp:
        store = ResultStore(Path(tmp))
        store.record_execution(
            tc_id="TC-SYS-001",
            testing_status="PASS",
            tester="GitHub Actions",
            run_id="12345",
            run_url="https://example.com/runs/12345",
            commit_sha="abc123",
            links=["SYS-001"],
            title="Object creation",
            reviewer="Alice",
            review_date="2026-01-15",
            review_status="approved",
        )
        record = store.get("TC-SYS-001")

    assert record["testing_status"] == "PASS"
    assert record["tester"] == "GitHub Actions"
    assert record["run_id"] == "12345"
    assert record["links"] == ["SYS-001"]
    assert record["title"] == "Object creation"
    assert record["reviewer"] == "Alice"
    assert record["review_date"] == "2026-01-15"
    assert record["review_status"] == "approved"


# ---------------------------------------------------------------------------
# TC-SRS-010-007: Tests with no TC ID are silently skipped
# ---------------------------------------------------------------------------

def test_TC_SRS_010_007_tests_without_tc_id_skipped():
    """
    TC-SRS-010-007: parse_junit_xml silently skips testcases with no
    recognisable TC ID in name or properties.

    @test_id: TC-SRS-010-007
    @links: SRS-010
    """
    with tempfile.TemporaryDirectory() as tmp:
        xml_path = Path(tmp) / "results.xml"
        _write_junit_xml(xml_path, [
            {"name": "test_login_flow"},
            {"name": "test_button_click"},
            {"name": "test_TC_SYS_001_valid"},
        ])
        results = parse_junit_xml(xml_path)

    assert len(results) == 1
    assert results[0].id == "TC-SYS-001"
