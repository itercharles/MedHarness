"""Tests for cr_closure_gate()."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from click.testing import CliRunner

from dhfkit.cli import main as dhfkit_main
from medharness.cli import main
from medharness.services.ci import cr_closure_gate


def _make_dhf(tmp_path: Path) -> Path:
    dhf = tmp_path / "DHF"
    CliRunner().invoke(dhfkit_main, ["--dhf", str(dhf), "init"])
    return dhf


def _write_spec(dhf: Path, cr_id: str, proposed: list[dict]) -> None:
    specs_dir = dhf / "documents" / "specs"
    specs_dir.mkdir(parents=True, exist_ok=True)
    lines = ["---", "disposition: approve", "proposed_new_items:"]
    for item in proposed:
        lines.append(f"  - type: {item['type']}")
        lines.append(f"    title: \"{item['title']}\"")
    lines += ["---", "", "# Spec body"]
    (specs_dir / f"{cr_id}-Spec.md").write_text("\n".join(lines) + "\n")


def _write_srs_item(dhf: Path, item_id: str, verification_method: list[str] | None = None) -> None:
    items_dir = dhf / "items" / "03_srs"
    lines = [f"id: {item_id}", f"title: Item {item_id}", "status: draft"]
    if verification_method:
        lines.append("verification_method:")
        for v in verification_method:
            lines.append(f"  - {v}")
    (items_dir / f"{item_id}.yaml").write_text("\n".join(lines) + "\n")


def _make_junit(tmp_path: Path, passing_links: list[str]) -> Path:
    root = ET.Element("testsuites")
    suite = ET.SubElement(root, "testsuite", name="suite", tests=str(len(passing_links)))
    for link in passing_links:
        tc = ET.SubElement(suite, "testcase", name=f"test_{link}", classname="Tests")
        props = ET.SubElement(tc, "properties")
        ET.SubElement(props, "property", name="medharness.links", value=link)
    path = tmp_path / "results.xml"
    ET.ElementTree(root).write(str(path))
    return path


# ---------------------------------------------------------------------------
# Service-level tests
# ---------------------------------------------------------------------------


def test_no_spec_file_passes_with_no_items(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path)
    result = cr_closure_gate("CR-001", dhf)
    assert result["passed"] is True
    assert result["missing_items"] == []


def test_proposed_items_all_created_passes(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path)
    _write_spec(dhf, "CR-001", [
        {"type": "SRS", "title": "Req A"},
        {"type": "SRS", "title": "Req B"},
    ])
    _write_srs_item(dhf, "SRS-001", verification_method=["Test"])
    _write_srs_item(dhf, "SRS-002", verification_method=["Test"])
    junit = _make_junit(tmp_path, ["SRS-001", "SRS-002"])
    result = cr_closure_gate("CR-001", dhf, junit_paths=(junit,))
    assert result["passed"] is True
    assert result["missing_items"] == []


def test_missing_proposed_item_fails(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path)
    _write_spec(dhf, "CR-001", [
        {"type": "SRS", "title": "Req A"},
        {"type": "SRS", "title": "Req B"},
    ])
    _write_srs_item(dhf, "SRS-001", verification_method=["Test"])
    # Only one of two proposed SRS items created
    result = cr_closure_gate("CR-001", dhf)
    assert result["passed"] is False
    assert any(m["type"] == "SRS" for m in result["missing_items"])


def test_item_without_verification_method_fails(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path)
    _write_spec(dhf, "CR-001", [{"type": "SRS", "title": "Req A"}])
    _write_srs_item(dhf, "SRS-001")  # no verification_method
    result = cr_closure_gate("CR-001", dhf)
    assert result["passed"] is False
    ids = [i["id"] for i in result["verification_gaps"]]
    assert "SRS-001" in ids


def test_test_method_without_junit_evidence_fails(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path)
    _write_spec(dhf, "CR-001", [{"type": "SRS", "title": "Req A"}])
    _write_srs_item(dhf, "SRS-001", verification_method=["Test"])
    junit = _make_junit(tmp_path, [])  # no passing TCs
    result = cr_closure_gate("CR-001", dhf, junit_paths=(junit,))
    assert result["passed"] is False
    ids = [i["id"] for i in result["unverified_test"]]
    assert "SRS-001" in ids


# ---------------------------------------------------------------------------
# CLI integration test
# ---------------------------------------------------------------------------


def test_cli_cr_complete_passes(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path)
    _write_spec(dhf, "CR-001", [{"type": "SRS", "title": "Req A"}])
    _write_srs_item(dhf, "SRS-001", verification_method=["Test"])
    junit = _make_junit(tmp_path, ["SRS-001"])
    result = CliRunner().invoke(
        main,
        ["--dhf", str(dhf), "ci", "cr-complete",
         "--cr", "CR-001", "--junit", str(junit)],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.splitlines()[0])
    assert payload["passed"] is True
    assert payload["cr_id"] == "CR-001"


def test_cli_cr_complete_fails_on_missing_items(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path)
    _write_spec(dhf, "CR-001", [
        {"type": "SRS", "title": "R1"},
        {"type": "SRS", "title": "R2"},
    ])
    _write_srs_item(dhf, "SRS-001", verification_method=["Test"])
    result = CliRunner().invoke(
        main,
        ["--dhf", str(dhf), "ci", "cr-complete", "--cr", "CR-001"],
    )
    assert result.exit_code != 0
