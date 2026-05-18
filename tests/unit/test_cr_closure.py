"""Tests for cr_closure_gate()."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

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


def _write_srs_item(
    dhf: Path,
    item_id: str,
    title: str,
    verification_method: list[str] | None = None,
) -> None:
    items_dir = dhf / "items" / "03_srs"
    lines = [f"id: {item_id}", f"title: {title}", "status: draft"]
    if verification_method:
        lines.append("verification_method:")
        for v in verification_method:
            lines.append(f"  - {v}")
    (items_dir / f"{item_id}.yaml").write_text("\n".join(lines) + "\n")


def _write_risk_item(dhf: Path, item_id: str, title: str) -> None:
    items_dir = dhf / "items" / "10_risk"
    items_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        f"id: {item_id}", f"title: {title}",
        "hazard: example", "cause: example", "effect: example",
        "severity_pre: S1", "probability_pre: P1",
        "severity_post: S1", "probability_post: P1",
        "risk_acceptability: Acceptable",
    ]
    (items_dir / f"{item_id}.yaml").write_text("\n".join(lines) + "\n")


def _write_rcm_item(dhf: Path, item_id: str, title: str, mitigates: str) -> None:
    items_dir = dhf / "items" / "11_rcm"
    items_dir.mkdir(parents=True, exist_ok=True)
    lines = [f"id: {item_id}", f"title: {title}", f"mitigates:\n  - {mitigates}"]
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


def test_no_spec_file_passes(tmp_path: Path) -> None:
    """No spec → no proposed items → closure check is vacuously satisfied."""
    dhf = _make_dhf(tmp_path)
    result = cr_closure_gate("CR-001", dhf)
    assert result["passed"] is True
    assert result["missing_items"] == []


def test_proposed_items_all_created_with_junit_passes(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path)
    _write_spec(dhf, "CR-001", [
        {"type": "SRS", "title": "Req A"},
        {"type": "SRS", "title": "Req B"},
    ])
    _write_srs_item(dhf, "SRS-001", "Req A", verification_method=["Test"])
    _write_srs_item(dhf, "SRS-002", "Req B", verification_method=["Test"])
    junit = _make_junit(tmp_path, ["SRS-001", "SRS-002"])
    result = cr_closure_gate("CR-001", dhf, junit_paths=(junit,))
    assert result["passed"] is True
    assert result["missing_items"] == []


def test_missing_proposed_item_by_title_fails(tmp_path: Path) -> None:
    """Item with wrong title does not satisfy a proposed item."""
    dhf = _make_dhf(tmp_path)
    _write_spec(dhf, "CR-001", [{"type": "SRS", "title": "Req A"}])
    # Item exists but has a different title — should not match
    _write_srs_item(dhf, "SRS-001", "Something unrelated", verification_method=["Test"])
    junit = _make_junit(tmp_path, ["SRS-001"])
    result = cr_closure_gate("CR-001", dhf, junit_paths=(junit,))
    assert result["passed"] is False
    assert any(m["type"] == "SRS" for m in result["missing_items"])


def test_title_match_is_case_insensitive(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path)
    _write_spec(dhf, "CR-001", [{"type": "SRS", "title": "Rate Limit Input Validation"}])
    # Title matches case-insensitively
    _write_srs_item(dhf, "SRS-001", "rate limit input validation", verification_method=["Inspection"])
    result = cr_closure_gate("CR-001", dhf)
    assert result["missing_items"] == []


def test_pre_existing_item_does_not_satisfy_proposed_item(tmp_path: Path) -> None:
    """A pre-existing SRS item with the same type but wrong title must not count.

    Regression: the old count-based check accepted any SRS item regardless of
    whether it was created by this CR. Title-matching prevents that false pass.
    """
    dhf = _make_dhf(tmp_path)
    _write_spec(dhf, "CR-001", [{"type": "SRS", "title": "New feature requirement"}])
    # Pre-existing item with a different title (e.g. from a previous CR)
    _write_srs_item(dhf, "SRS-099", "Old unrelated requirement", verification_method=["Test"])
    result = cr_closure_gate("CR-001", dhf)
    assert result["passed"] is False
    assert any(m["type"] == "SRS" for m in result["missing_items"])


def test_item_without_verification_method_fails(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path)
    _write_spec(dhf, "CR-001", [{"type": "SRS", "title": "Req A"}])
    _write_srs_item(dhf, "SRS-001", "Req A")  # no verification_method
    result = cr_closure_gate("CR-001", dhf)
    assert result["passed"] is False
    ids = [i["id"] for i in result["verification_gaps"]]
    assert "SRS-001" in ids


def test_test_method_without_junit_evidence_fails(tmp_path: Path) -> None:
    """Empty JUnit (no passing TCs) with Test method → fails."""
    dhf = _make_dhf(tmp_path)
    _write_spec(dhf, "CR-001", [{"type": "SRS", "title": "Req A"}])
    _write_srs_item(dhf, "SRS-001", "Req A", verification_method=["Test"])
    junit = _make_junit(tmp_path, [])
    result = cr_closure_gate("CR-001", dhf, junit_paths=(junit,))
    assert result["passed"] is False
    ids = [i["id"] for i in result["unverified_test"]]
    assert "SRS-001" in ids


def test_test_method_with_no_junit_at_all_fails(tmp_path: Path) -> None:
    """No JUnit provided at all with Test method → fails at closure.

    Regression: the old behavior silently passed when junit_paths=() because
    validate_verification_completeness treated missing evidence as 'not yet checked'.
    The closure gate must require evidence (enforce_test_evidence=True).
    """
    dhf = _make_dhf(tmp_path)
    _write_spec(dhf, "CR-001", [{"type": "SRS", "title": "Req A"}])
    _write_srs_item(dhf, "SRS-001", "Req A", verification_method=["Test"])
    result = cr_closure_gate("CR-001", dhf, junit_paths=())
    assert result["passed"] is False
    ids = [i["id"] for i in result["unverified_test"]]
    assert "SRS-001" in ids


def test_proposed_item_with_empty_title_is_skipped(tmp_path: Path) -> None:
    """Malformed proposed entry (empty title) is skipped, not treated as a wildcard match."""
    dhf = _make_dhf(tmp_path)
    _write_spec(dhf, "CR-001", [
        {"type": "SRS", "title": ""},          # empty title — should be skipped
        {"type": "SRS", "title": "Real req"},  # valid entry — must be present
    ])
    _write_srs_item(dhf, "SRS-001", "Real req", verification_method=["Inspection"])
    result = cr_closure_gate("CR-001", dhf)
    # empty-title entry skipped; "Real req" present → passes
    assert result["passed"] is True
    assert result["missing_items"] == []


def test_risk_rcm_in_proposed_items_passes_without_verification_method(tmp_path: Path) -> None:
    """RISK and RCM items do not have verification_method — closure must not require it."""
    dhf = _make_dhf(tmp_path)
    _write_spec(dhf, "CR-001", [
        {"type": "RISK", "title": "Unintended data modification"},
        {"type": "RCM", "title": "Optimistic-lock concurrency control"},
    ])
    _write_risk_item(dhf, "RISK-002", "Unintended data modification")
    _write_rcm_item(dhf, "RCM-002", "Optimistic-lock concurrency control", "RISK-002")
    result = cr_closure_gate("CR-001", dhf)
    assert result["passed"] is True
    assert result["missing_items"] == []
    assert result["verification_gaps"] == []


def test_risk_rcm_missing_from_dhf_fails(tmp_path: Path) -> None:
    """Proposed RISK item not created → closure fails."""
    dhf = _make_dhf(tmp_path)
    _write_spec(dhf, "CR-001", [
        {"type": "RISK", "title": "Unintended data modification"},
    ])
    # No RISK item with that title created
    result = cr_closure_gate("CR-001", dhf)
    assert result["passed"] is False
    assert any(m["type"] == "RISK" for m in result["missing_items"])


def test_mixed_srs_and_risk_in_proposed_items(tmp_path: Path) -> None:
    """SRS requires verification_method; RISK does not. Both in proposed_new_items."""
    dhf = _make_dhf(tmp_path)
    _write_spec(dhf, "CR-001", [
        {"type": "SRS", "title": "Req A"},
        {"type": "RISK", "title": "New hazard from Req A"},
    ])
    _write_srs_item(dhf, "SRS-001", "Req A", verification_method=["Inspection"])
    _write_risk_item(dhf, "RISK-002", "New hazard from Req A")
    result = cr_closure_gate("CR-001", dhf)
    assert result["passed"] is True
    assert result["missing_items"] == []
    assert result["verification_gaps"] == []


# ---------------------------------------------------------------------------
# CLI integration tests
# ---------------------------------------------------------------------------


def test_cli_cr_complete_passes(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path)
    _write_spec(dhf, "CR-001", [{"type": "SRS", "title": "Req A"}])
    _write_srs_item(dhf, "SRS-001", "Req A", verification_method=["Test"])
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


def test_cli_cr_complete_fails_on_missing_item(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path)
    _write_spec(dhf, "CR-001", [{"type": "SRS", "title": "Missing req"}])
    # No item with matching title created
    result = CliRunner().invoke(
        main,
        ["--dhf", str(dhf), "ci", "cr-complete", "--cr", "CR-001"],
    )
    assert result.exit_code != 0


def test_cli_cr_complete_fails_without_junit_for_test_items(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path)
    _write_spec(dhf, "CR-001", [{"type": "SRS", "title": "Req A"}])
    _write_srs_item(dhf, "SRS-001", "Req A", verification_method=["Test"])
    result = CliRunner().invoke(
        main,
        ["--dhf", str(dhf), "ci", "cr-complete", "--cr", "CR-001"],
    )
    assert result.exit_code != 0
