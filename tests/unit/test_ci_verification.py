"""Unit tests for verify verification (validate_verification_completeness)."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from click.testing import CliRunner

from dhfkit.cli import main as dhfkit_main
from medharness.cli import main
from medharness.services.ci import ENVELOPE_KEYS
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
    ids = [i["id"] for i in result["details"]["missing_method"]]
    assert "SRS-001" in ids


def test_item_with_test_method_and_passing_tc_passes(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path, [{"id": "SRS-001", "title": "With test", "verification_method": ["Test"]}])
    junit = _make_junit(tmp_path, ["SRS-001"])
    result = validate_verification_completeness(dhf, junit_paths=[junit])
    assert result["passed"]
    assert not result["details"]["unverified_test"]


def test_item_with_test_method_but_no_junit_is_unverified(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path, [{"id": "SRS-001", "title": "Test gap", "verification_method": ["Test"]}])
    junit = _make_junit(tmp_path, [])  # no passing tests
    result = validate_verification_completeness(dhf, junit_paths=[junit])
    assert not result["passed"]
    ids = [i["id"] for i in result["details"]["unverified_test"]]
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
    ids = [i["id"] for i in result["details"]["manual_review_required"]]
    assert "SRS-001" in ids


def test_mixed_test_and_inspection_covered_by_test(tmp_path: Path) -> None:
    """When an item has both Test and Inspection, a passing TC satisfies Test."""
    dhf = _make_dhf(tmp_path, [
        {"id": "SRS-001", "verification_method": ["Test", "Inspection"]}
    ])
    junit = _make_junit(tmp_path, ["SRS-001"])
    result = validate_verification_completeness(dhf, junit_paths=[junit])
    assert result["passed"]
    assert not result["details"]["unverified_test"]


def test_multiple_items_mixed_results(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path, [
        {"id": "SRS-001", "verification_method": ["Test"]},
        {"id": "SRS-002", "verification_method": ["Test"]},
        {"id": "SRS-003"},  # missing method
    ])
    junit = _make_junit(tmp_path, ["SRS-001"])  # only SRS-001 covered
    result = validate_verification_completeness(dhf, junit_paths=[junit])
    assert not result["passed"]
    assert any(i["id"] == "SRS-003" for i in result["details"]["missing_method"])
    assert any(i["id"] == "SRS-002" for i in result["details"]["unverified_test"])
    assert not any(i["id"] == "SRS-001" for i in result["details"]["unverified_test"])


def test_req_types_filter(tmp_path: Path) -> None:
    """Only the specified req types are checked."""
    dhf = _make_dhf(tmp_path, [{"id": "SRS-001"}])
    result = validate_verification_completeness(dhf, req_types=("SYS",))
    # SRS-001 should not appear — only SYS is checked and there are no SYS items
    assert result["passed"]
    assert not result["details"]["missing_method"]


def test_custom_type_code_not_in_defaults_is_checked_when_specified(tmp_path: Path) -> None:
    """A fully custom doc type (e.g. SYSREQ, not in the default SRS/SYS/CRS set) must be
    checked when explicitly included in req_types — the gate must resolve via the configured
    prefix, not by comparing uid.split('-')[0] against a hardcoded set."""
    dhf = _make_dhf(tmp_path, [])
    # Register a custom doc type not in the defaults
    custom_cfg = dhf / "config" / "doc_types" / "sysreq.yaml"
    custom_cfg.write_text(
        "code: SYSREQ\nrole: system_requirement\nname: System Requirement\n"
        "prefix: SYSREQ-\ndirectory: 99_sysreq\nproperties:\n- id\n"
        "- name: title\n  format: short_text\n  label: Title\n"
        "has_verification: true\nverification_states:\n- not_verified\n- verified\n"
    )
    items_dir = dhf / "items" / "99_sysreq"
    items_dir.mkdir(parents=True, exist_ok=True)
    (items_dir / "SYSREQ-001.yaml").write_text(
        "id: SYSREQ-001\ntitle: Custom req\nstatus: draft\n"
    )
    result = validate_verification_completeness(dhf, req_types=("SYSREQ",))
    assert not result["passed"]
    ids = [i["id"] for i in result["details"]["missing_method"]]
    assert "SYSREQ-001" in ids, f"Expected SYSREQ-001 in missing_method; got {ids}"


# ---------------------------------------------------------------------------
# CLI integration tests
# ---------------------------------------------------------------------------


def test_cli_validate_verification_passes(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path, [{"id": "SRS-001", "verification_method": ["Test"]}])
    junit = _make_junit(tmp_path, ["SRS-001"])
    result = CliRunner().invoke(
        main,
        ["--dhf", str(dhf), "verify", "verification",
         "--dhf", str(dhf), "--junit", str(junit)],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.splitlines()[0])
    assert payload["passed"] is True


def test_cli_validate_verification_fails_on_missing_method(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path, [{"id": "SRS-001", "title": "No method"}])
    result = CliRunner().invoke(
        main,
        ["--dhf", str(dhf), "verify", "verification", "--dhf", str(dhf)],
    )
    assert result.exit_code != 0


def test_cli_validate_verification_json_stdout(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path, [{"id": "SRS-001", "verification_method": ["Test"]}])
    result = CliRunner().invoke(
        main,
        ["--dhf", str(dhf), "verify", "verification", "--dhf", str(dhf)],
    )
    payload = json.loads(result.output.splitlines()[0])
    assert set(payload) == set(ENVELOPE_KEYS)
    assert {"missing_method", "unverified_test",
            "manual_review_required"} <= payload["details"].keys()
