"""Tests for cr_closure_gate()."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

from click.testing import CliRunner

from medharness.cli import main
from medharness.services.verify_completion import cr_closure_gate
from dhfkit.tests.fixtures import bare_dhf


def _make_dhf(tmp_path: Path) -> Path:
    dhf = tmp_path / "DHF"
    bare_dhf(dhf)
    return dhf


def _write_cr(
    dhf: Path,
    cr_id: str,
    affected: list[str] | None,
    *,
    implementation_notes: str | None = "Implementation plan: do the thing.",
    affected_risk_items: list[str] | None = (),
    triage_result: dict | None = {"verdict": "approved"},  # noqa: B006 — never mutated
) -> None:
    """Write a CR with the fields `build plan` records. ``None`` omits a field."""
    cr_dir = dhf / "items" / "07_cr"
    cr_dir.mkdir(parents=True, exist_ok=True)
    lines = [f"id: {cr_id}", 'title: "Test CR"']
    if implementation_notes is not None:
        lines.append(f"implementation_notes: {implementation_notes!r}")
    for name, value in (("affected_risk_items", affected_risk_items), ("affected_items", affected)):
        if value is not None:
            lines.append(f"{name}: {json.dumps(list(value))}")
    if triage_result is not None:
        lines.append(f"triage_result:\n  verdict: {triage_result.get('verdict', '')}")
    (cr_dir / f"{cr_id}.yaml").write_text("\n".join(lines) + "\n")


def _write_srs_item(dhf: Path, item_id: str, verification_method: list[str] | None = None) -> None:
    lines = [f"id: {item_id}", f"title: {item_id} title", "status: draft"]
    if verification_method:
        lines.append(f"verification_method: {json.dumps(verification_method)}")
    (dhf / "items" / "03_srs" / f"{item_id}.yaml").write_text("\n".join(lines) + "\n")


def _write_risk_item(dhf: Path, item_id: str) -> None:
    items_dir = dhf / "items" / "10_risk"
    items_dir.mkdir(parents=True, exist_ok=True)
    (items_dir / f"{item_id}.yaml").write_text("\n".join([
        f"id: {item_id}", "title: A hazard",
        "hazard: example", "cause: example", "effect: example",
        "severity_pre: S1", "probability_pre: P1",
        "severity_post: S1", "probability_post: P1",
        "risk_acceptability: Acceptable",
    ]) + "\n")


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


def _incomplete(result: dict) -> list[str]:
    return [f["field"] for f in result["details"]["incomplete_cr_fields"]]


# ---------------------------------------------------------------------------
# The CR's record
# ---------------------------------------------------------------------------


def test_absent_cr_item_fails(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path)
    result = cr_closure_gate("CR-001", dhf)
    assert result["passed"] is False
    assert "affected_items" in _incomplete(result)


def test_missing_affected_items_fails(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path)
    _write_cr(dhf, "CR-001", None)
    result = cr_closure_gate("CR-001", dhf)
    assert result["passed"] is False
    assert _incomplete(result) == ["affected_items"]
    assert any("affected_items" in e for e in result["errors"])


def test_empty_affected_items_passes(tmp_path: Path) -> None:
    """A CR that changed no items says so with []."""
    dhf = _make_dhf(tmp_path)
    _write_cr(dhf, "CR-001", [])
    result = cr_closure_gate("CR-001", dhf)
    assert result["passed"] is True, result["errors"]
    assert result["details"]["missing_items"] == []


def test_missing_implementation_notes_fails(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path)
    _write_cr(dhf, "CR-001", [], implementation_notes=None)
    assert "implementation_notes" in _incomplete(cr_closure_gate("CR-001", dhf))


def test_empty_implementation_notes_fails(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path)
    _write_cr(dhf, "CR-001", [], implementation_notes="")
    assert "implementation_notes" in _incomplete(cr_closure_gate("CR-001", dhf))


def test_missing_affected_risk_items_fails(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path)
    _write_cr(dhf, "CR-001", [], affected_risk_items=None)
    assert "affected_risk_items" in _incomplete(cr_closure_gate("CR-001", dhf))


def test_null_affected_risk_items_fails(tmp_path: Path) -> None:
    """Only an explicit list is an answer."""
    dhf = _make_dhf(tmp_path)
    cr_dir = dhf / "items" / "07_cr"
    cr_dir.mkdir(parents=True, exist_ok=True)
    (cr_dir / "CR-001.yaml").write_text(
        'id: CR-001\ntitle: "Test CR"\n'
        "implementation_notes: 'plan'\n"
        "affected_risk_items: null\n"
        "affected_items: []\n"
        "triage_result:\n  verdict: approved\n"
    )
    assert "affected_risk_items" in _incomplete(cr_closure_gate("CR-001", dhf))


def test_missing_triage_result_fails(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path)
    _write_cr(dhf, "CR-001", [], triage_result=None)
    assert "triage_result" in _incomplete(cr_closure_gate("CR-001", dhf))


def test_triage_result_not_approved_fails(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path)
    _write_cr(dhf, "CR-001", [], triage_result={"verdict": "rejected"})
    assert "triage_result" in _incomplete(cr_closure_gate("CR-001", dhf))


# ---------------------------------------------------------------------------
# The affected items
# ---------------------------------------------------------------------------


def test_affected_items_present_and_verified_passes(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path)
    _write_cr(dhf, "CR-001", ["SRS-010", "SRS-011"])
    _write_srs_item(dhf, "SRS-010", ["Test"])
    _write_srs_item(dhf, "SRS-011", ["Test"])
    junit = _make_junit(tmp_path, ["SRS-010", "SRS-011"])
    result = cr_closure_gate("CR-001", dhf, junit_paths=(junit,))
    assert result["passed"] is True, result["errors"]


def test_an_affected_item_absent_from_the_dhf_fails(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path)
    _write_cr(dhf, "CR-001", ["SRS-404"])
    result = cr_closure_gate("CR-001", dhf)
    assert result["passed"] is False
    assert result["details"]["missing_items"] == ["SRS-404"]
    assert any("SRS-404" in e for e in result["errors"])


def test_item_without_verification_method_fails(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path)
    _write_cr(dhf, "CR-001", ["SRS-010"])
    _write_srs_item(dhf, "SRS-010")
    result = cr_closure_gate("CR-001", dhf)
    assert result["passed"] is False
    assert [i["id"] for i in result["details"]["verification_gaps"]] == ["SRS-010"]


def test_test_method_without_junit_evidence_fails(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path)
    _write_cr(dhf, "CR-001", ["SRS-010"])
    _write_srs_item(dhf, "SRS-010", ["Test"])
    junit = _make_junit(tmp_path, [])
    result = cr_closure_gate("CR-001", dhf, junit_paths=(junit,))
    assert result["passed"] is False
    assert "SRS-010" in [i["id"] for i in result["details"]["unverified_test"]]


def test_test_method_with_no_junit_at_all_fails(tmp_path: Path) -> None:
    """Closure requires evidence; no JUnit is not 'not yet checked'."""
    dhf = _make_dhf(tmp_path)
    _write_cr(dhf, "CR-001", ["SRS-010"])
    _write_srs_item(dhf, "SRS-010", ["Test"])
    result = cr_closure_gate("CR-001", dhf, junit_paths=())
    assert result["passed"] is False
    assert "SRS-010" in [i["id"] for i in result["details"]["unverified_test"]]


def test_risk_items_need_no_verification_method(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path)
    _write_cr(dhf, "CR-001", ["RISK-002", "SRS-010"])
    _write_risk_item(dhf, "RISK-002")
    _write_srs_item(dhf, "SRS-010", ["Inspection"])
    result = cr_closure_gate("CR-001", dhf)
    assert result["passed"] is True, result["errors"]
    assert result["details"]["verification_gaps"] == []


def test_an_item_the_cr_did_not_touch_is_not_its_problem(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path)
    _write_cr(dhf, "CR-001", ["SRS-010"])
    _write_srs_item(dhf, "SRS-010", ["Inspection"])
    _write_srs_item(dhf, "SRS-099")  # no method, not this CR's
    result = cr_closure_gate("CR-001", dhf)
    assert result["passed"] is True, result["errors"]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _cli(dhf: Path, *args: str):
    return CliRunner().invoke(main, ["--dhf", str(dhf), "verify", "completion", "--cr", "CR-001", *args])


def test_cli_passes(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path)
    _write_cr(dhf, "CR-001", ["SRS-010"])
    _write_srs_item(dhf, "SRS-010", ["Test"])
    junit = _make_junit(tmp_path, ["SRS-010"])
    result = _cli(dhf, "--junit", str(junit))
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.splitlines()[0])
    assert payload["passed"] is True
    assert "CR-001" in payload["summary"]


def test_cli_fails_on_incomplete_cr_fields(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path)
    _write_cr(dhf, "CR-001", [], implementation_notes=None, affected_risk_items=None)
    result = _cli(dhf)
    assert result.exit_code != 0
    payload = json.loads(result.output.splitlines()[0])
    assert payload["passed"] is False
    assert len(payload["errors"]) >= 2, payload["errors"]
    assert "FAIL [completion]" in result.output


def test_cli_names_a_missing_item(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path)
    _write_cr(dhf, "CR-001", ["SRS-404"])
    result = _cli(dhf)
    assert result.exit_code != 0
    assert "FAIL [completion] SRS-404" in result.output
