"""Unit tests for ci validate-verification (validate_verification_completeness)."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from click.testing import CliRunner

from dhfkit.cli import main as dhfkit_main
from medharness.cli import main
from medharness.services.ci import validate_verification_completeness


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_dhf(tmp_path: Path, items: list[dict]) -> Path:
    """Bootstrap a minimal DHF with the given items and return its path."""
    dhf = tmp_path / "DHF"
    CliRunner().invoke(dhfkit_main, ["--dhf", str(dhf), "init"])
    items_dir = dhf / "items" / "03_srs"
    for item in items:
        fname = f"{item['id']}.yaml"
        lines = [f"id: {item['id']}", f"title: {item.get('title', 'Test item')}",
                 f"status: draft"]
        if "verification_method" in item:
            vm = item["verification_method"]
            if isinstance(vm, list):
                lines.append("verification_method:")
                for v in vm:
                    lines.append(f"  - {v}")
            else:
                lines.append(f"verification_method: {vm}")
        (items_dir / fname).write_text("\n".join(lines) + "\n")
    return dhf


def _make_junit(tmp_path: Path, passing_links: list[str], filename: str = "results.xml") -> Path:
    root = ET.Element("testsuites")
    suite = ET.SubElement(root, "testsuite", name="suite", tests=str(len(passing_links)))
    for link in passing_links:
        tc = ET.SubElement(suite, "testcase", name=f"test_{link}", classname="Tests")
        props = ET.SubElement(tc, "properties")
        ET.SubElement(props, "property", name="medharness.links", value=link)
    path = tmp_path / filename
    ET.ElementTree(root).write(str(path))
    return path


# ---------------------------------------------------------------------------
# Service-level tests
# ---------------------------------------------------------------------------


def test_missing_verification_method_is_reported(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path, [{"id": "SRS-001", "title": "No method"}])
    result = validate_verification_completeness(dhf)
    assert not result["passed"]
    ids = [i["id"] for i in result["missing_method"]]
    assert "SRS-001" in ids


def test_item_with_test_method_and_passing_tc_passes(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path, [{"id": "SRS-001", "title": "With test", "verification_method": ["Test"]}])
    junit = _make_junit(tmp_path, ["SRS-001"])
    result = validate_verification_completeness(dhf, junit_paths=[junit])
    assert result["passed"]
    assert not result["unverified_test"]


def test_item_with_test_method_but_no_junit_is_unverified(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path, [{"id": "SRS-001", "title": "Test gap", "verification_method": ["Test"]}])
    junit = _make_junit(tmp_path, [])  # no passing tests
    result = validate_verification_completeness(dhf, junit_paths=[junit])
    assert not result["passed"]
    ids = [i["id"] for i in result["unverified_test"]]
    assert "SRS-001" in ids


def test_no_junit_paths_does_not_fail_test_items(tmp_path: Path) -> None:
    """Without JUnit evidence, Test-method items are NOT a gate failure."""
    dhf = _make_dhf(tmp_path, [{"id": "SRS-001", "verification_method": ["Test"]}])
    result = validate_verification_completeness(dhf, junit_paths=[])
    assert result["passed"]


def test_inspection_method_surfaced_as_manual_review_required(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path, [{"id": "SRS-001", "verification_method": ["Inspection"]}])
    result = validate_verification_completeness(dhf)
    assert result["passed"]  # not a gate failure
    ids = [i["id"] for i in result["manual_review_required"]]
    assert "SRS-001" in ids


def test_mixed_test_and_inspection_covered_by_test(tmp_path: Path) -> None:
    """When an item has both Test and Inspection, a passing TC satisfies Test."""
    dhf = _make_dhf(tmp_path, [
        {"id": "SRS-001", "verification_method": ["Test", "Inspection"]}
    ])
    junit = _make_junit(tmp_path, ["SRS-001"])
    result = validate_verification_completeness(dhf, junit_paths=[junit])
    assert result["passed"]
    assert not result["unverified_test"]


def test_multiple_items_mixed_results(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path, [
        {"id": "SRS-001", "verification_method": ["Test"]},
        {"id": "SRS-002", "verification_method": ["Test"]},
        {"id": "SRS-003"},  # missing method
    ])
    junit = _make_junit(tmp_path, ["SRS-001"])  # only SRS-001 covered
    result = validate_verification_completeness(dhf, junit_paths=[junit])
    assert not result["passed"]
    assert any(i["id"] == "SRS-003" for i in result["missing_method"])
    assert any(i["id"] == "SRS-002" for i in result["unverified_test"])
    assert not any(i["id"] == "SRS-001" for i in result["unverified_test"])


def test_req_types_filter(tmp_path: Path) -> None:
    """Only the specified req types are checked."""
    dhf = _make_dhf(tmp_path, [{"id": "SRS-001"}])
    result = validate_verification_completeness(dhf, req_types=("SYS",))
    # SRS-001 should not appear — only SYS is checked and there are no SYS items
    assert result["passed"]
    assert not result["missing_method"]


# ---------------------------------------------------------------------------
# CLI integration tests
# ---------------------------------------------------------------------------


def test_cli_validate_verification_passes(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path, [{"id": "SRS-001", "verification_method": ["Test"]}])
    junit = _make_junit(tmp_path, ["SRS-001"])
    result = CliRunner().invoke(
        main,
        ["--dhf", str(dhf), "ci", "validate-verification",
         "--dhf", str(dhf), "--junit", str(junit)],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.splitlines()[0])
    assert payload["passed"] is True


def test_cli_validate_verification_fails_on_missing_method(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path, [{"id": "SRS-001", "title": "No method"}])
    result = CliRunner().invoke(
        main,
        ["--dhf", str(dhf), "ci", "validate-verification", "--dhf", str(dhf)],
    )
    assert result.exit_code != 0


def test_cli_validate_verification_json_stdout(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path, [{"id": "SRS-001", "verification_method": ["Test"]}])
    result = CliRunner().invoke(
        main,
        ["--dhf", str(dhf), "ci", "validate-verification", "--dhf", str(dhf)],
    )
    payload = json.loads(result.output.splitlines()[0])
    assert "passed" in payload
    assert "missing_method" in payload
    assert "unverified_test" in payload
    assert "manual_review_required" in payload
    assert "summary" in payload
