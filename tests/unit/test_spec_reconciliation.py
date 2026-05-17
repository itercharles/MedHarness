"""Tests for spec-to-artifact reconciliation in validate_generate_dhf."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from dhfkit.cli import main as dhfkit_main
from medharness.services.design_validation import _validate_spec_reconciliation


def _make_dhf(tmp_path: Path) -> Path:
    dhf = tmp_path / "DHF"
    CliRunner().invoke(dhfkit_main, ["--dhf", str(dhf), "init"])
    return dhf


def _write_spec(dhf: Path, cr_id: str, proposed: list[dict]) -> Path:
    specs_dir = dhf / "documents" / "specs"
    specs_dir.mkdir(parents=True, exist_ok=True)
    spec_path = specs_dir / f"{cr_id}-Spec.md"
    lines = ["---", "disposition: approve", "proposed_new_items:"]
    for item in proposed:
        lines.append(f"  - type: {item['type']}")
        lines.append(f"    title: \"{item['title']}\"")
    lines += ["---", "", "# Spec body"]
    spec_path.write_text("\n".join(lines) + "\n")
    return spec_path


def test_no_spec_file_returns_no_errors(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path)
    errors = _validate_spec_reconciliation("CR-001", dhf, [])
    assert errors == []


def test_spec_with_no_proposed_items_returns_no_errors(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path)
    specs_dir = dhf / "documents" / "specs"
    specs_dir.mkdir(parents=True, exist_ok=True)
    (specs_dir / "CR-001-Spec.md").write_text(
        "---\ndisposition: approve\nproposed_new_items: []\n---\n"
    )
    errors = _validate_spec_reconciliation("CR-001", dhf, [])
    assert errors == []


def test_exact_match_returns_no_errors(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path)
    _write_spec(dhf, "CR-001", [
        {"type": "SRS", "title": "First req"},
        {"type": "SRS", "title": "Second req"},
    ])
    # Two SRS items created
    errors = _validate_spec_reconciliation("CR-001", dhf, ["SRS-001", "SRS-002"])
    assert errors == []


def test_fewer_created_than_proposed_is_error(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path)
    _write_spec(dhf, "CR-001", [
        {"type": "SRS", "title": "First req"},
        {"type": "SRS", "title": "Second req"},
    ])
    # Only one SRS created
    errors = _validate_spec_reconciliation("CR-001", dhf, ["SRS-001"])
    assert len(errors) == 1
    assert errors[0]["field"] == "spec_reconciliation.SRS"
    assert "2" in errors[0]["issue"]
    assert "1" in errors[0]["issue"]


def test_missing_type_entirely_is_error(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path)
    _write_spec(dhf, "CR-001", [
        {"type": "SRS", "title": "Some req"},
        {"type": "SYS", "title": "A system req"},
    ])
    # Only SRS created, no SYS
    errors = _validate_spec_reconciliation("CR-001", dhf, ["SRS-001"])
    fields = [e["field"] for e in errors]
    assert "spec_reconciliation.SYS" in fields
    assert "spec_reconciliation.SRS" not in fields


def test_more_created_than_proposed_is_not_an_error(tmp_path: Path) -> None:
    """Extra items beyond what was proposed are allowed — LLM may create supporting items."""
    dhf = _make_dhf(tmp_path)
    _write_spec(dhf, "CR-001", [{"type": "SRS", "title": "One req"}])
    errors = _validate_spec_reconciliation("CR-001", dhf, ["SRS-001", "SRS-002", "SRS-003"])
    assert errors == []


def test_multiple_type_shortfalls_reported_separately(tmp_path: Path) -> None:
    dhf = _make_dhf(tmp_path)
    _write_spec(dhf, "CR-001", [
        {"type": "SRS", "title": "R1"},
        {"type": "SRS", "title": "R2"},
        {"type": "SYS", "title": "S1"},
        {"type": "SYS", "title": "S2"},
    ])
    errors = _validate_spec_reconciliation("CR-001", dhf, [])
    fields = {e["field"] for e in errors}
    assert "spec_reconciliation.SRS" in fields
    assert "spec_reconciliation.SYS" in fields
