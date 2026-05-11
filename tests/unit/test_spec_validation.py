"""Tests for medharness.services.spec_validation."""

import json
from pathlib import Path

import pytest

from medharness.services.spec_validation import (
    extract_structured_analysis,
    parse_spec_frontmatter,
    read_spec_json,
    validate_spec,
    write_spec_json,
)


_VALID_FM = """\
---
cr_id: "CR-001"
direction_fit: "in-scope"
affected_items:
  - SYS-001
proposed_new_items: []
design_impact_summary: "Update persistence requirements and tests."
test_plan:
  auto_covered:
    - TC-SYS-001-001
  needs_new_tc: []
  must_be_manual: []
---

## Problem Summary

Some text.
"""


def _write_spec(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "CR-001-Spec.md"
    p.write_text(content, encoding="utf-8")
    return p


def _valid_fm_dict() -> dict:
    return {
        "cr_id": "CR-001",
        "direction_fit": "in-scope",
        "affected_items": ["SYS-001"],
        "proposed_new_items": [],
        "design_impact_summary": "Test summary.",
        "test_plan": {"auto_covered": [], "needs_new_tc": [], "must_be_manual": []},
    }


def test_parse_valid_frontmatter(tmp_path):
    path = _write_spec(tmp_path, _VALID_FM)
    fm = parse_spec_frontmatter(path)
    assert fm is not None
    assert fm["cr_id"] == "CR-001"
    assert fm["direction_fit"] == "in-scope"
    assert "SYS-001" in fm["affected_items"]


def test_parse_no_frontmatter(tmp_path):
    path = tmp_path / "spec.md"
    path.write_text("# No front-matter here\n", encoding="utf-8")
    assert parse_spec_frontmatter(path) is None


def test_parse_missing_file(tmp_path):
    assert parse_spec_frontmatter(tmp_path / "missing.md") is None


def test_validate_valid_spec(tmp_path):
    path = _write_spec(tmp_path, _VALID_FM)
    errors = validate_spec(path, "CR-001")
    assert errors == []


def test_validate_missing_file(tmp_path):
    errors = validate_spec(tmp_path / "missing.md", "CR-001")
    assert len(errors) == 1
    assert errors[0]["field"] == "file"
    assert errors[0]["fix"]


def test_validate_no_frontmatter(tmp_path):
    path = tmp_path / "spec.md"
    path.write_text("# No front-matter\n", encoding="utf-8")
    errors = validate_spec(path, "CR-001")
    assert any(e["field"] == "front-matter" for e in errors)


def test_validate_wrong_cr_id(tmp_path):
    path = _write_spec(tmp_path, _VALID_FM)
    errors = validate_spec(path, "CR-999")
    assert any(e["field"] == "cr_id" for e in errors)
    assert any(e["fix"] for e in errors if e["field"] == "cr_id")


def test_validate_invalid_direction_fit(tmp_path):
    content = _VALID_FM.replace('direction_fit: "in-scope"', 'direction_fit: "unknown"')
    path = _write_spec(tmp_path, content)
    errors = validate_spec(path, "CR-001")
    assert any(e["field"] == "direction_fit" for e in errors)
    fix = next(e["fix"] for e in errors if e["field"] == "direction_fit")
    assert "in-scope" in fix


def test_validate_missing_direction_fit(tmp_path):
    content = _VALID_FM.replace('direction_fit: "in-scope"\n', "")
    path = _write_spec(tmp_path, content)
    errors = validate_spec(path, "CR-001")
    assert any(e["field"] == "direction_fit" for e in errors)


def test_validate_missing_test_plan(tmp_path):
    lines = [l for l in _VALID_FM.splitlines()
             if not l.startswith("test_plan") and "auto_covered" not in l
             and "needs_new_tc" not in l and "must_be_manual" not in l
             and "TC-SYS" not in l]
    content = "\n".join(lines)
    path = _write_spec(tmp_path, content)
    errors = validate_spec(path, "CR-001")
    assert any("test_plan" in e["field"] for e in errors)


def test_validate_missing_proposed_new_items(tmp_path):
    content = _VALID_FM.replace("proposed_new_items: []\n", "")
    path = _write_spec(tmp_path, content)
    errors = validate_spec(path, "CR-001")
    assert any(e["field"] == "proposed_new_items" for e in errors)


def test_validate_proposed_new_items_not_a_list(tmp_path):
    content = _VALID_FM.replace("proposed_new_items: []", "proposed_new_items: not-a-list")
    path = _write_spec(tmp_path, content)
    errors = validate_spec(path, "CR-001")
    assert any(e["field"] == "proposed_new_items" for e in errors)


def test_validate_invalid_proposed_new_item_entry(tmp_path):
    content = _VALID_FM.replace(
        "proposed_new_items: []",
        'proposed_new_items:\n  - type: UNKNOWN\n    title: ""',
    )
    path = _write_spec(tmp_path, content)
    errors = validate_spec(path, "CR-001")
    fields = {e["field"] for e in errors}
    assert "proposed_new_items[0].type" in fields
    assert "proposed_new_items[0].title" in fields


def test_validate_proposed_new_items_entry_missing_type(tmp_path):
    content = _VALID_FM.replace(
        "proposed_new_items: []",
        "proposed_new_items:\n  - title: 'The system shall...'",
    )
    path = _write_spec(tmp_path, content)
    errors = validate_spec(path, "CR-001")
    assert any(e["field"] == "proposed_new_items[0].type" for e in errors)


def test_validate_proposed_new_items_entry_missing_title(tmp_path):
    content = _VALID_FM.replace(
        "proposed_new_items: []",
        "proposed_new_items:\n  - type: SRS",
    )
    path = _write_spec(tmp_path, content)
    errors = validate_spec(path, "CR-001")
    assert any(e["field"] == "proposed_new_items[0].title" for e in errors)


def test_validate_proposed_new_items_entry_not_a_dict(tmp_path):
    content = _VALID_FM.replace(
        "proposed_new_items: []",
        "proposed_new_items:\n  - just a string",
    )
    path = _write_spec(tmp_path, content)
    errors = validate_spec(path, "CR-001")
    assert any(e["field"] == "proposed_new_items[0]" for e in errors)


def test_validate_proposed_new_items_valid_entry_passes(tmp_path):
    content = _VALID_FM.replace(
        "proposed_new_items: []",
        "proposed_new_items:\n  - type: SRS\n    title: 'The system shall display...'",
    )
    path = _write_spec(tmp_path, content)
    errors = validate_spec(path, "CR-001")
    assert not any("proposed_new_items" in e["field"] for e in errors)


def test_validate_missing_design_impact_summary(tmp_path):
    content = _VALID_FM.replace('design_impact_summary: "Update persistence requirements and tests."\n', "")
    path = _write_spec(tmp_path, content)
    errors = validate_spec(path, "CR-001")
    assert any(e["field"] == "design_impact_summary" for e in errors)


def test_validate_empty_design_impact_summary(tmp_path):
    content = _VALID_FM.replace(
        'design_impact_summary: "Update persistence requirements and tests."',
        'design_impact_summary: ""',
    )
    path = _write_spec(tmp_path, content)
    errors = validate_spec(path, "CR-001")
    assert any(e["field"] == "design_impact_summary" for e in errors)


def test_validate_design_impact_summary_not_string(tmp_path):
    content = _VALID_FM.replace(
        'design_impact_summary: "Update persistence requirements and tests."',
        "design_impact_summary: 42",
    )
    path = _write_spec(tmp_path, content)
    errors = validate_spec(path, "CR-001")
    assert any(e["field"] == "design_impact_summary" for e in errors)


def test_validate_test_plan_missing_keys(tmp_path):
    content = _VALID_FM.replace(
        "test_plan:\n  auto_covered:\n    - TC-SYS-001-001\n  needs_new_tc: []\n  must_be_manual: []",
        "test_plan:\n  auto_covered: []",
    )
    path = _write_spec(tmp_path, content)
    errors = validate_spec(path, "CR-001")
    missing_keys = {e["field"] for e in errors}
    assert "test_plan.needs_new_tc" in missing_keys
    assert "test_plan.must_be_manual" in missing_keys


def test_validate_test_plan_key_must_be_list(tmp_path):
    content = _VALID_FM.replace(
        "test_plan:\n  auto_covered:\n    - TC-SYS-001-001\n  needs_new_tc: []\n  must_be_manual: []",
        'test_plan:\n  auto_covered: "TC-SYS-001-001"\n  needs_new_tc: []\n  must_be_manual: []',
    )
    path = _write_spec(tmp_path, content)
    errors = validate_spec(path, "CR-001")
    assert any(e["field"] == "test_plan.auto_covered" for e in errors)


def test_validate_test_plan_manual_entries_must_be_list(tmp_path):
    content = _VALID_FM.replace(
        "test_plan:\n  auto_covered:\n    - TC-SYS-001-001\n  needs_new_tc: []\n  must_be_manual: []",
        'test_plan:\n  auto_covered: []\n  needs_new_tc: []\n  must_be_manual: "manual check"',
    )
    path = _write_spec(tmp_path, content)
    errors = validate_spec(path, "CR-001")
    assert any(e["field"] == "test_plan.must_be_manual" for e in errors)


def test_validate_all_errors_have_fix(tmp_path):
    path = _write_spec(tmp_path, "---\ncr_id: wrong\n---\n")
    errors = validate_spec(path, "CR-001")
    for error in errors:
        assert "fix" in error and error["fix"], f"Error missing fix: {error}"


def test_extract_structured_analysis(tmp_path):
    path = _write_spec(tmp_path, _VALID_FM)
    analysis = extract_structured_analysis(path)
    assert analysis is not None
    assert analysis["direction_fit"] == "in-scope"
    assert analysis["affected_items"] == ["SYS-001"]
    assert analysis["proposed_new_items"] == []
    assert analysis["design_impact_summary"] == "Update persistence requirements and tests."
    assert analysis["test_plan"]["auto_covered"] == ["TC-SYS-001-001"]


def test_write_spec_json_creates_file(tmp_path):
    spec_path = tmp_path / "CR-001-Spec.md"
    spec_path.write_text("", encoding="utf-8")
    write_spec_json(spec_path, _valid_fm_dict())
    assert (tmp_path / "CR-001-Spec.json").exists()


def test_write_spec_json_returns_correct_path(tmp_path):
    spec_path = tmp_path / "CR-001-Spec.md"
    spec_path.write_text("", encoding="utf-8")
    result = write_spec_json(spec_path, _valid_fm_dict())
    assert result == tmp_path / "CR-001-Spec.json"


def test_write_spec_json_writes_all_frontmatter_keys(tmp_path):
    spec_path = tmp_path / "CR-001-Spec.md"
    spec_path.write_text("", encoding="utf-8")
    fm = _valid_fm_dict()
    write_spec_json(spec_path, fm)
    written = json.loads((tmp_path / "CR-001-Spec.json").read_text(encoding="utf-8"))
    assert written == fm


def test_read_spec_json_returns_none_when_missing(tmp_path):
    spec_path = tmp_path / "CR-001-Spec.md"
    assert read_spec_json(spec_path) is None


def test_read_spec_json_returns_dict_when_present(tmp_path):
    spec_path = tmp_path / "CR-001-Spec.md"
    spec_path.write_text("", encoding="utf-8")
    fm = _valid_fm_dict()
    write_spec_json(spec_path, fm)
    result = read_spec_json(spec_path)
    assert result == fm


def test_read_spec_json_returns_none_on_invalid_json(tmp_path):
    spec_path = tmp_path / "CR-001-Spec.md"
    (tmp_path / "CR-001-Spec.json").write_text("not valid json {{{{", encoding="utf-8")
    assert read_spec_json(spec_path) is None


def test_write_then_read_roundtrip(tmp_path):
    spec_path = tmp_path / "CR-042-Spec.md"
    spec_path.write_text("", encoding="utf-8")
    fm = _valid_fm_dict()
    fm["cr_id"] = "CR-042"
    write_spec_json(spec_path, fm)
    result = read_spec_json(spec_path)
    assert result == fm
