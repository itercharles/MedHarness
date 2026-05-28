"""Tests for medharness dhf context for-stage command."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from dhfkit.cli import main as dhfkit_main
from medharness.cli import main


def _make_dhf(tmp_path: Path) -> Path:
    dhf = tmp_path / "DHF"
    CliRunner().invoke(dhfkit_main, ["--dhf", str(dhf), "init"])
    return dhf


def _write_cr(dhf: Path, cr_id: str, **fields) -> None:
    """Write a CR item YAML. Field values must be str, list[str|dict], or dict."""
    import importlib.resources
    cr_src = importlib.resources.files("dhfkit").joinpath("templates/config/doc_types/cr.yaml")
    (dhf / "config" / "doc_types" / "cr.yaml").write_bytes(cr_src.read_bytes())
    cr_dir = dhf / "items" / "07_cr"
    cr_dir.mkdir(parents=True, exist_ok=True)
    lines = [f"id: {cr_id}", f'title: "Test CR"']
    for k, v in fields.items():
        if isinstance(v, str):
            lines.append(f"{k}: {repr(v)}")
        elif isinstance(v, list):
            if not v:
                lines.append(f"{k}: []")
            else:
                lines.append(f"{k}:")
                for item in v:
                    lines.append(f"  - {repr(item) if isinstance(item, str) else item}")
        elif isinstance(v, dict):
            lines.append(f"{k}:")
            for dk, dv in v.items():
                lines.append(f"  {dk}: {repr(dv)}")
    (cr_dir / f"{cr_id}.yaml").write_text("\n".join(lines) + "\n")


def _invoke(dhf: Path, stage: str, cr_id: str = "CR-001") -> dict:
    result = CliRunner().invoke(
        main,
        ["--dhf", str(dhf), "dhf", "context", "for-stage", stage, "--cr", cr_id],
    )
    assert result.exit_code == 0, result.output
    return json.loads(result.output.splitlines()[0])


class TestForStageDesign:
    def test_returns_full_item_list(self, tmp_path: Path) -> None:
        dhf = _make_dhf(tmp_path)
        _write_cr(dhf, "CR-001")
        payload = _invoke(dhf, "design")
        assert payload["stage"] == "design"
        assert "items" in payload
        assert "item_count" in payload

    def test_includes_full_cr_item(self, tmp_path: Path) -> None:
        """design stage returns the full CR item, not just id/title/status summary."""
        dhf = _make_dhf(tmp_path)
        _write_cr(dhf, "CR-001", triage_result={"verdict": "approved"})
        payload = _invoke(dhf, "design")
        cr = payload["cr"]
        assert cr["id"] == "CR-001"
        # Full item has triage_result, not just the id/title/status summary
        assert "triage_result" in cr

    def test_no_affected_items_key(self, tmp_path: Path) -> None:
        """design stage does not use affected_items (empty at start of generate-dhf)."""
        dhf = _make_dhf(tmp_path)
        _write_cr(dhf, "CR-001")
        payload = _invoke(dhf, "design")
        assert "affected_items" not in payload


class TestForStageDevelop:
    def test_includes_implementation_notes(self, tmp_path: Path) -> None:
        dhf = _make_dhf(tmp_path)
        notes = "Implementation plan: do the thing."
        _write_cr(dhf, "CR-001", implementation_notes=notes)
        payload = _invoke(dhf, "develop")
        assert payload["cr"]["implementation_notes"] == notes

    def test_includes_proposed_new_items(self, tmp_path: Path) -> None:
        dhf = _make_dhf(tmp_path)
        _write_cr(dhf, "CR-001", implementation_notes="plan")
        payload = _invoke(dhf, "develop")
        assert "proposed_new_items" in payload["cr"]

    def test_includes_triage_result(self, tmp_path: Path) -> None:
        dhf = _make_dhf(tmp_path)
        _write_cr(dhf, "CR-001",
                  implementation_notes="plan",
                  triage_result={"verdict": "approved"})
        payload = _invoke(dhf, "develop")
        assert payload["cr"].get("triage_result", {}).get("verdict") == "approved"

    def test_missing_implementation_notes_returns_empty_string(self, tmp_path: Path) -> None:
        """CR without implementation_notes → field present but empty, not absent."""
        dhf = _make_dhf(tmp_path)
        _write_cr(dhf, "CR-001")
        payload = _invoke(dhf, "develop")
        assert payload["cr"]["implementation_notes"] == ""

    def test_affected_items_include_verification_criteria(self, tmp_path: Path) -> None:
        """Affected items in develop stage include verification_criteria field."""
        dhf = _make_dhf(tmp_path)
        srs_dir = dhf / "items" / "03_srs"
        (srs_dir / "SRS-001.yaml").write_text(
            "id: SRS-001\ntitle: Rate limit\n"
            "verification_criteria: Response ≤ 200 ms at p95.\n"
        )
        _write_cr(dhf, "CR-001",
                  implementation_notes="plan",
                  affected_items=["SRS-001"])
        payload = _invoke(dhf, "develop")
        items = payload.get("affected_items", [])
        assert len(items) == 1
        assert items[0]["verification_criteria"] == "Response ≤ 200 ms at p95."
