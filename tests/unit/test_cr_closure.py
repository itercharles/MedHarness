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
    # dhfkit init only registers sys/srs/risk/rcm; add CR so the closure gate
    # can write and read CR items via the adapter.
    import importlib.resources
    cr_src = importlib.resources.files("dhfkit").joinpath("templates/config/doc_types/cr.yaml")
    (dhf / "config" / "doc_types" / "cr.yaml").write_bytes(cr_src.read_bytes())
    return dhf


def _write_cr_proposed(
    dhf: Path,
    cr_id: str,
    proposed: list[dict],
    *,
    implementation_notes: str | None = "Implementation plan: do the thing.",
    affected_risk_items=...,  # ... → write []; None → omit field; list → write that list
    triage_result=...,        # ... → write {"verdict": "approved"}; None → omit; dict → write it
) -> None:
    """Write proposed_new_items and mandatory closure fields into the CR item YAML.

    Pass ``None`` for any keyword arg to omit that field (tests the absence case).
    Use ``...`` (default) to write the minimal valid value.
    """
    ari = [] if affected_risk_items is ... else affected_risk_items
    tr = {"verdict": "approved"} if triage_result is ... else triage_result

    cr_dir = dhf / "items" / "07_cr"
    cr_dir.mkdir(parents=True, exist_ok=True)
    lines = [f"id: {cr_id}", 'title: "Test CR"']
    if implementation_notes is not None:
        lines.append(f"implementation_notes: {repr(implementation_notes)}")
    if ari is not None:
        lines.append("affected_risk_items: []" if not ari else "affected_risk_items:")
        for uid in ari or []:
            lines.append(f"  - {uid}")
    if tr is not None:
        lines.append("triage_result:")
        lines.append(f"  verdict: {tr.get('verdict', '')}")
    if not proposed:
        lines.append("proposed_new_items: []")
    else:
        lines.append("proposed_new_items:")
        for item in proposed:
            lines.append(f"  - type: {item['type']}")
            lines.append(f"    title: \"{item['title']}\"")
    (cr_dir / f"{cr_id}.yaml").write_text("\n".join(lines) + "\n")


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


def test_missing_proposed_new_items_fails(tmp_path: Path) -> None:
    """CR item with no proposed_new_items field → closure gate fails with actionable message."""
    dhf = _make_dhf(tmp_path)
    # Write a CR item without the proposed_new_items field
    cr_dir = dhf / "items" / "07_cr"
    cr_dir.mkdir(parents=True, exist_ok=True)
    (cr_dir / "CR-001.yaml").write_text('id: CR-001\ntitle: "Test CR"\n')
    result = cr_closure_gate("CR-001", dhf)
    assert result["passed"] is False
    assert "proposed_new_items" in result["summary"]


def test_absent_cr_item_fails(tmp_path: Path) -> None:
    """No CR item at all → closure gate fails (generate-dhf Step 4 not run)."""
    dhf = _make_dhf(tmp_path)
    result = cr_closure_gate("CR-001", dhf)
    assert result["passed"] is False
    assert result["missing_items"] == []


def test_empty_proposed_new_items_passes(tmp_path: Path) -> None:
    """Explicitly empty proposed_new_items → no artifact reconciliation required → passes."""
    dhf = _make_dhf(tmp_path)
    _write_cr_proposed(dhf, "CR-001", [])
    result = cr_closure_gate("CR-001", dhf)
    assert result["passed"] is True
    assert result["missing_items"] == []
    assert result["incomplete_cr_fields"] == []


def test_missing_implementation_notes_fails(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path)
    _write_cr_proposed(dhf, "CR-001", [], implementation_notes=None)
    result = cr_closure_gate("CR-001", dhf)
    assert result["passed"] is False
    fields = [f["field"] for f in result["incomplete_cr_fields"]]
    assert "implementation_notes" in fields


def test_empty_implementation_notes_fails(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path)
    _write_cr_proposed(dhf, "CR-001", [], implementation_notes="")
    result = cr_closure_gate("CR-001", dhf)
    assert result["passed"] is False
    fields = [f["field"] for f in result["incomplete_cr_fields"]]
    assert "implementation_notes" in fields


def test_missing_affected_risk_items_fails(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path)
    _write_cr_proposed(dhf, "CR-001", [], affected_risk_items=None)
    result = cr_closure_gate("CR-001", dhf)
    assert result["passed"] is False
    fields = [f["field"] for f in result["incomplete_cr_fields"]]
    assert "affected_risk_items" in fields


def test_empty_affected_risk_items_passes(tmp_path: Path) -> None:
    """affected_risk_items: [] is valid — means agent confirmed no risk items apply."""
    dhf = _make_dhf(tmp_path)
    _write_cr_proposed(dhf, "CR-001", [], affected_risk_items=[])
    result = cr_closure_gate("CR-001", dhf)
    assert result["passed"] is True
    assert all(f["field"] != "affected_risk_items" for f in result["incomplete_cr_fields"])


def test_missing_triage_result_fails(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path)
    _write_cr_proposed(dhf, "CR-001", [], triage_result=None)
    result = cr_closure_gate("CR-001", dhf)
    assert result["passed"] is False
    fields = [f["field"] for f in result["incomplete_cr_fields"]]
    assert "triage_result" in fields


def test_triage_result_not_approved_fails(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path)
    _write_cr_proposed(dhf, "CR-001", [], triage_result={"verdict": "rejected"})
    result = cr_closure_gate("CR-001", dhf)
    assert result["passed"] is False
    fields = [f["field"] for f in result["incomplete_cr_fields"]]
    assert "triage_result" in fields


def test_all_cr_fields_present_passes(tmp_path: Path) -> None:
    """All three mandatory CR fields present → incomplete_cr_fields is empty."""
    dhf = _make_dhf(tmp_path)
    _write_cr_proposed(
        dhf, "CR-001", [],
        implementation_notes="## Overview\nDo the thing.",
        affected_risk_items=[],
        triage_result={"verdict": "approved"},
    )
    result = cr_closure_gate("CR-001", dhf)
    assert result["incomplete_cr_fields"] == []


def test_proposed_items_all_created_with_junit_passes(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path)
    _write_cr_proposed(dhf, "CR-001", [
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
    _write_cr_proposed(dhf, "CR-001", [{"type": "SRS", "title": "Req A"}])
    # Item exists but has a different title — should not match
    _write_srs_item(dhf, "SRS-001", "Something unrelated", verification_method=["Test"])
    junit = _make_junit(tmp_path, ["SRS-001"])
    result = cr_closure_gate("CR-001", dhf, junit_paths=(junit,))
    assert result["passed"] is False
    assert any(m["type"] == "SRS" for m in result["missing_items"])


def test_title_match_is_case_insensitive(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path)
    _write_cr_proposed(dhf, "CR-001", [{"type": "SRS", "title": "Rate Limit Input Validation"}])
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
    _write_cr_proposed(dhf, "CR-001", [{"type": "SRS", "title": "New feature requirement"}])
    # Pre-existing item with a different title (e.g. from a previous CR)
    _write_srs_item(dhf, "SRS-099", "Old unrelated requirement", verification_method=["Test"])
    result = cr_closure_gate("CR-001", dhf)
    assert result["passed"] is False
    assert any(m["type"] == "SRS" for m in result["missing_items"])


def test_item_without_verification_method_fails(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path)
    _write_cr_proposed(dhf, "CR-001", [{"type": "SRS", "title": "Req A"}])
    _write_srs_item(dhf, "SRS-001", "Req A")  # no verification_method
    result = cr_closure_gate("CR-001", dhf)
    assert result["passed"] is False
    ids = [i["id"] for i in result["verification_gaps"]]
    assert "SRS-001" in ids


def test_test_method_without_junit_evidence_fails(tmp_path: Path) -> None:
    """Empty JUnit (no passing TCs) with Test method → fails."""
    dhf = _make_dhf(tmp_path)
    _write_cr_proposed(dhf, "CR-001", [{"type": "SRS", "title": "Req A"}])
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
    _write_cr_proposed(dhf, "CR-001", [{"type": "SRS", "title": "Req A"}])
    _write_srs_item(dhf, "SRS-001", "Req A", verification_method=["Test"])
    result = cr_closure_gate("CR-001", dhf, junit_paths=())
    assert result["passed"] is False
    ids = [i["id"] for i in result["unverified_test"]]
    assert "SRS-001" in ids


def test_proposed_item_with_empty_title_is_skipped(tmp_path: Path) -> None:
    """Malformed proposed entry (empty title) is skipped, not treated as a wildcard match."""
    dhf = _make_dhf(tmp_path)
    _write_cr_proposed(dhf, "CR-001", [
        {"type": "SRS", "title": ""},          # empty title — should be skipped
        {"type": "SRS", "title": "Real req"},  # valid entry — must be present
    ])
    _write_srs_item(dhf, "SRS-001", "Real req", verification_method=["Inspection"])
    result = cr_closure_gate("CR-001", dhf)
    assert result["passed"] is True
    assert result["missing_items"] == []


def test_duplicate_proposed_entries_deduplicated(tmp_path: Path) -> None:
    """Two identical proposed entries with one real item → passes (deduplication).

    Duplicate entries in proposed_new_items are an LLM authoring quirk. One
    real DHF item satisfies both identical promises — deduplicate before checking.
    """
    dhf = _make_dhf(tmp_path)
    _write_cr_proposed(dhf, "CR-001", [
        {"type": "SRS", "title": "Same title"},
        {"type": "SRS", "title": "Same title"},  # duplicate
    ])
    _write_srs_item(dhf, "SRS-001", "Same title", verification_method=["Inspection"])
    result = cr_closure_gate("CR-001", dhf)
    assert result["passed"] is True
    assert result["missing_items"] == []


def test_risk_rcm_in_proposed_items_passes_without_verification_method(tmp_path: Path) -> None:
    """RISK and RCM items do not have verification_method — closure must not require it."""
    dhf = _make_dhf(tmp_path)
    _write_cr_proposed(dhf, "CR-001", [
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
    _write_cr_proposed(dhf, "CR-001", [{"type": "RISK", "title": "Unintended data modification"}])
    result = cr_closure_gate("CR-001", dhf)
    assert result["passed"] is False
    assert any(m["type"] == "RISK" for m in result["missing_items"])


def test_mixed_srs_and_risk_in_proposed_items(tmp_path: Path) -> None:
    """SRS requires verification_method; RISK does not. Both in proposed_new_items."""
    dhf = _make_dhf(tmp_path)
    _write_cr_proposed(dhf, "CR-001", [
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
    _write_cr_proposed(dhf, "CR-001", [{"type": "SRS", "title": "Req A"}])
    _write_srs_item(dhf, "SRS-001", "Req A", verification_method=["Test"])
    junit = _make_junit(tmp_path, ["SRS-001"])
    result = CliRunner().invoke(
        main,
        ["--dhf", str(dhf), "verify", "completion",
         "--cr", "CR-001", "--junit", str(junit)],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.splitlines()[0])
    assert payload["passed"] is True
    assert payload["cr_id"] == "CR-001"


def test_cli_cr_complete_fails_on_incomplete_cr_fields(tmp_path: Path) -> None:
    """CLI prints FAIL [cr-complete] lines for each missing mandatory CR field."""
    dhf = _make_dhf(tmp_path)
    _write_cr_proposed(dhf, "CR-001", [], implementation_notes=None, affected_risk_items=None)
    result = CliRunner().invoke(
        main,
        ["--dhf", str(dhf), "verify", "completion", "--cr", "CR-001"],
    )
    assert result.exit_code != 0
    payload = json.loads(result.output.splitlines()[0])
    assert payload["passed"] is False
    assert len(payload["incomplete_cr_fields"]) >= 2
    assert "FAIL [cr-complete]" in result.output


def test_cli_cr_complete_fails_on_missing_item(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path)
    _write_cr_proposed(dhf, "CR-001", [{"type": "SRS", "title": "Missing req"}])
    # No item with matching title created
    result = CliRunner().invoke(
        main,
        ["--dhf", str(dhf), "verify", "completion", "--cr", "CR-001"],
    )
    assert result.exit_code != 0


def test_cli_cr_complete_fails_without_junit_for_test_items(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path)
    _write_cr_proposed(dhf, "CR-001", [{"type": "SRS", "title": "Req A"}])
    _write_srs_item(dhf, "SRS-001", "Req A", verification_method=["Test"])
    result = CliRunner().invoke(
        main,
        ["--dhf", str(dhf), "verify", "completion", "--cr", "CR-001"],
    )
    assert result.exit_code != 0
