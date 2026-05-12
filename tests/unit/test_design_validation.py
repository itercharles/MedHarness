"""Unit tests for medharness.services.design_validation."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from medharness.services.design_validation import validate_design


def _write_spec(path: Path, affected: list[str], proposed_new_items: list[dict] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    affected_yaml = "\n".join(f"  - {uid}" for uid in affected) if affected else " []"
    proposed = proposed_new_items or []
    if proposed:
        proposed_yaml = "\n".join(
            f"  - type: {item['type']}\n    title: \"{item['title']}\""
            for item in proposed
        )
        proposed_block = f"proposed_new_items:\n{proposed_yaml}\n"
    else:
        proposed_block = "proposed_new_items: []\n"
    body = (
        "---\n"
        'cr_id: "CR-001"\n'
        'direction_fit: "in-scope"\n'
        f"affected_items:{(' ' + affected_yaml.lstrip()) if not affected else chr(10) + affected_yaml}\n"
        f"{proposed_block}"
        "test_plan:\n"
        "  auto_covered: []\n"
        "  needs_new_tc: []\n"
        "  must_be_manual: []\n"
        "---\n"
    )
    path.write_text(body, encoding="utf-8")


@pytest.fixture
def repo(tmp_path: Path) -> tuple[Path, Path]:
    dhf = tmp_path / "DHF"
    dhf.mkdir()
    spec = tmp_path / "docs" / "cr-specs" / "CR-001-Spec.md"
    return dhf, spec


class TestValidateDesignSchema:
    def test_returns_no_errors_when_all_clean(self, repo):
        dhf, spec = repo
        _write_spec(spec, ["SYS-001"])
        with patch("dhfkit.api.validate_schema", return_value={"valid": True, "errors": []}), \
             patch("dhfkit.api.validate_traceability", return_value={"passed": True}), \
             patch("dhfkit.api.list_items", return_value=[{"id": "SYS-001"}]):
            errors = validate_design("CR-001", dhf, spec)
        assert errors == []

    def test_schema_failure_produces_error(self, repo):
        dhf, spec = repo
        _write_spec(spec, [])
        with patch("dhfkit.api.validate_schema",
                   return_value={"valid": False, "errors": ["bad yaml at SYS-001.yaml"]}), \
             patch("dhfkit.api.validate_traceability", return_value={"passed": True}), \
             patch("dhfkit.api.list_items", return_value=[]):
            errors = validate_design("CR-001", dhf, spec)
        assert any(e["field"] == "schema" for e in errors)
        assert any("SYS-001.yaml" in e["issue"] for e in errors)

    def test_schema_exception_produces_error(self, repo):
        dhf, spec = repo
        _write_spec(spec, [])
        with patch("dhfkit.api.validate_schema", side_effect=RuntimeError("boom")), \
             patch("dhfkit.api.validate_traceability", return_value={"passed": True}), \
             patch("dhfkit.api.list_items", return_value=[]):
            errors = validate_design("CR-001", dhf, spec)
        assert any(e["field"] == "schema" and "boom" in e["issue"] for e in errors)


class TestValidateDesignTraceability:
    def test_required_traceability_failure(self, repo):
        dhf, spec = repo
        _write_spec(spec, [])
        trace = {
            "passed": False,
            "required": {
                "passed": False,
                "failures": [{
                    "id": "SRS-002",
                    "field": "derives_from",
                    "target_type": "SYS",
                    "min_count": 1,
                    "issue": "SRS derives_from → SYS (count=0, need ≥1)",
                }],
            },
            "orphans": [],
            "coverage": [],
        }
        with patch("dhfkit.api.validate_schema", return_value={"valid": True, "errors": []}), \
             patch("dhfkit.api.validate_traceability", return_value=trace), \
             patch("dhfkit.api.list_items", return_value=[]):
            errors = validate_design("CR-001", dhf, spec)
        assert any("SRS-002" in e["issue"] and "SYS" in e["fix"] for e in errors)

    def test_orphan_produces_error(self, repo):
        dhf, spec = repo
        _write_spec(spec, [])
        trace = {
            "passed": False,
            "required": {"passed": True, "failures": []},
            "orphans": [{
                "id": "SRS-003",
                "required_parents": ["SYS"],
                "issue": "No link to any of ['SYS']",
            }],
            "coverage": [],
        }
        with patch("dhfkit.api.validate_schema", return_value={"valid": True, "errors": []}), \
             patch("dhfkit.api.validate_traceability", return_value=trace), \
             patch("dhfkit.api.list_items", return_value=[]):
            errors = validate_design("CR-001", dhf, spec)
        orphan_errors = [e for e in errors if e["field"] == "traceability.orphan"]
        assert orphan_errors and "SRS-003" in orphan_errors[0]["issue"]

    def test_coverage_gap_produces_error(self, repo):
        dhf, spec = repo
        _write_spec(spec, [])
        trace = {
            "passed": False,
            "required": {"passed": True, "failures": []},
            "orphans": [],
            "coverage": [{
                "matrix": "main",
                "parent_type": "SYS",
                "child_type": "SRS",
                "total": 2,
                "covered": 1,
                "uncovered": ["SYS-002"],
                "passed": False,
            }],
        }
        with patch("dhfkit.api.validate_schema", return_value={"valid": True, "errors": []}), \
             patch("dhfkit.api.validate_traceability", return_value=trace), \
             patch("dhfkit.api.list_items", return_value=[]):
            errors = validate_design("CR-001", dhf, spec)
        cov_errors = [e for e in errors if "coverage" in e["field"]]
        assert cov_errors and "SYS-002" in cov_errors[0]["issue"]


class TestValidateDesignAffectedItems:
    def test_missing_affected_item_produces_error(self, repo):
        dhf, spec = repo
        _write_spec(spec, ["SYS-001", "SRS-002"])
        with patch("dhfkit.api.validate_schema", return_value={"valid": True, "errors": []}), \
             patch("dhfkit.api.validate_traceability", return_value={"passed": True}), \
             patch("dhfkit.api.list_items", return_value=[{"id": "SYS-001"}]):
            errors = validate_design("CR-001", dhf, spec)
        missing = [e for e in errors if e["field"] == "affected_items"]
        assert len(missing) == 1
        assert "SRS-002" in missing[0]["issue"]

    def test_no_spec_returns_no_affected_errors(self, repo):
        dhf, _ = repo
        bogus_spec = repo[1]  # path that does not exist
        with patch("dhfkit.api.validate_schema", return_value={"valid": True, "errors": []}), \
             patch("dhfkit.api.validate_traceability", return_value={"passed": True}), \
             patch("dhfkit.api.list_items", return_value=[]):
            errors = validate_design("CR-001", dhf, bogus_spec)
        assert all(e["field"] != "affected_items" for e in errors)

    def test_empty_affected_list_skips_check(self, repo):
        dhf, spec = repo
        _write_spec(spec, [])
        with patch("dhfkit.api.validate_schema", return_value={"valid": True, "errors": []}), \
             patch("dhfkit.api.validate_traceability", return_value={"passed": True}), \
             patch("dhfkit.api.list_items", return_value=[]):
            errors = validate_design("CR-001", dhf, spec)
        assert all(e["field"] != "affected_items" for e in errors)


class TestValidateDesignProposedNewItems:
    def test_missing_proposed_new_item_produces_error(self, repo):
        dhf, spec = repo
        _write_spec(spec, [], proposed_new_items=[{"type": "SRS", "title": "New workflow requirement"}])
        with patch("dhfkit.api.validate_schema", return_value={"valid": True, "errors": []}), \
             patch("dhfkit.api.validate_traceability", return_value={"passed": True}), \
             patch("dhfkit.api.list_items", return_value=[{"id": "SYS-001", "type": "SYS", "title": "Existing"}]):
            errors = validate_design("CR-001", dhf, spec)
        proposed = [e for e in errors if e["field"] == "proposed_new_items[0]"]
        assert len(proposed) == 1
        assert "New workflow requirement" in proposed[0]["issue"]

    def test_existing_proposed_new_item_passes(self, repo):
        dhf, spec = repo
        _write_spec(spec, [], proposed_new_items=[{"type": "SRS", "title": "New workflow requirement"}])
        with patch("dhfkit.api.validate_schema", return_value={"valid": True, "errors": []}), \
             patch("dhfkit.api.validate_traceability", return_value={"passed": True}), \
             patch("dhfkit.api.list_items", return_value=[
                 {"id": "SRS-010", "type": "SRS", "title": "New workflow requirement"},
             ]):
            errors = validate_design("CR-001", dhf, spec)
        assert all(not e["field"].startswith("proposed_new_items") for e in errors)
