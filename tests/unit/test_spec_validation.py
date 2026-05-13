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
disposition: approve
pipeline_route: standard
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
        "disposition": "approve",
        "pipeline_route": "standard",
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
    assert fm["disposition"] == "approve"
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


def test_validate_legacy_direction_fit_spec_passes(tmp_path):
    content = _VALID_FM.replace("disposition: approve\npipeline_route: standard\n", 'direction_fit: "in-scope"\n')
    path = _write_spec(tmp_path, content)
    errors = validate_spec(path, "CR-001")
    assert errors == []


def test_validate_legacy_out_of_scope_with_empty_affected_items_passes(tmp_path):
    content = (
        "---\n"
        'cr_id: "CR-001"\n'
        'direction_fit: "out-of-scope"\n'
        "affected_items: []\n"
        "proposed_new_items: []\n"
        'design_impact_summary: ""\n'
        "test_plan:\n"
        "  auto_covered: []\n"
        "  needs_new_tc: []\n"
        "  must_be_manual: []\n"
        "---\n"
    )
    path = _write_spec(tmp_path, content)
    errors = validate_spec(path, "CR-001")
    assert not any(e["field"] == "affected_items" for e in errors)


def test_validate_legacy_out_of_scope_with_non_empty_affected_items_passes(tmp_path):
    content = (
        "---\n"
        'cr_id: "CR-001"\n'
        'direction_fit: "out-of-scope"\n'
        "affected_items:\n"
        "  - SYS-001\n"
        "proposed_new_items: []\n"
        'design_impact_summary: ""\n'
        "test_plan:\n"
        "  auto_covered: []\n"
        "  needs_new_tc: []\n"
        "  must_be_manual: []\n"
        "---\n"
    )
    path = _write_spec(tmp_path, content)
    errors = validate_spec(path, "CR-001")
    assert not any(e["field"] == "affected_items" for e in errors)


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


@pytest.mark.parametrize("content,field", [
    (_VALID_FM.replace("disposition: approve\n", ""), "disposition"),
    (_VALID_FM.replace("disposition: approve", "disposition: sideways"), "disposition"),
    (_VALID_FM.replace("disposition: approve\npipeline_route: standard\n", 'direction_fit: "sideways"\n'), "direction_fit"),
    (_VALID_FM.replace("pipeline_route: standard\n", ""), "pipeline_route"),
    (_VALID_FM.replace("pipeline_route: standard", "pipeline_route: waterfall"), "pipeline_route"),
    (_VALID_FM.replace("affected_items:\n  - SYS-001\n", ""), "affected_items"),
])
def test_validate_approve_field_errors(tmp_path, content, field):
    path = _write_spec(tmp_path, content)
    errors = validate_spec(path, "CR-001")
    assert any(e["field"] == field for e in errors)


@pytest.mark.parametrize("content,error_fields_present,error_fields_absent", [
    pytest.param(
        '---\ncr_id: "CR-001"\ndisposition: decline:out-of-scope\n---\n',
        {"decline_rationale"},
        set(),
        id="decline_without_rationale",
    ),
    pytest.param(
        '---\ncr_id: "CR-001"\ndisposition: decline:duplicate\ndecline_rationale: "Already implemented."\n---\n',
        set(),
        {"disposition", "decline_rationale"},
        id="decline_with_rationale_passes",
    ),
    pytest.param(
        '---\ncr_id: "CR-001"\ndisposition: hold:scope-expansion\n---\n',
        {"decline_rationale"},
        set(),
        id="hold_without_rationale",
    ),
    pytest.param(
        '---\ncr_id: "CR-001"\ndisposition: hold:scope-expansion\ndecline_rationale: "Needs roadmap approval."\npipeline_route: standard\n---\n',
        {"pipeline_route"},
        set(),
        id="hold_rejects_pipeline_route",
    ),
    pytest.param(
        '---\ncr_id: "CR-001"\ndirection_fit: "out-of-scope"\npipeline_route: standard\naffected_items: []\nproposed_new_items: []\ndesign_impact_summary: ""\ntest_plan:\n  auto_covered: []\n  needs_new_tc: []\n  must_be_manual: []\n---\n',
        set(),
        {"pipeline_route"},
        id="legacy_decline_with_pipeline_route_passes",
    ),
])
def test_validate_decline_disposition_rules(tmp_path, content, error_fields_present, error_fields_absent):
    path = _write_spec(tmp_path, content)
    errors = validate_spec(path, "CR-001")
    for field in error_fields_present:
        assert any(e["field"] == field for e in errors), f"expected error field {field}"
    for field in error_fields_absent:
        assert not any(e["field"] == field for e in errors), f"unexpected error field {field}"


@pytest.mark.parametrize("content,field,expect_present", [
    pytest.param(
        '---\ncr_id: "CR-001"\ndisposition: decline:out-of-scope\ndecline_rationale: "Outside product direction."\n---\n',
        "affected_items",
        False,
        id="decline_skips_affected_items",
    ),
    pytest.param(
        '---\ncr_id: "CR-001"\ndisposition: decline:architecture-conflict\ndecline_rationale: "Conflicts with ADR-001."\n---\n',
        "test_plan",
        False,
        id="decline_skips_test_plan",
    ),
    pytest.param(
        '---\ncr_id: "CR-001"\ndisposition: decline:out-of-scope\ndecline_rationale: "Outside product direction."\naffected_items:\n  - SYS-001\n---\n',
        "affected_items",
        True,
        id="decline_rejects_stale_affected_items",
    ),
    pytest.param(
        '---\ncr_id: "CR-001"\ndisposition: decline:architecture-conflict\ndecline_rationale: "Conflicts with ADR-001."\ntest_plan:\n  auto_covered:\n    - TC-SYS-001-001\n  needs_new_tc: []\n  must_be_manual: []\n---\n',
        "test_plan",
        True,
        id="decline_rejects_stale_test_plan",
    ),
])
def test_validate_decline_stale_fields(tmp_path, content, field, expect_present):
    path = _write_spec(tmp_path, content)
    errors = validate_spec(path, "CR-001")
    check = any(e["field"] == field or e["field"].startswith(f"{field}.") for e in errors)
    assert check if expect_present else not check


@pytest.mark.parametrize("replace_old,replace_new,field", [
    (
        "test_plan:\n  auto_covered:\n    - TC-SYS-001-001\n  needs_new_tc: []\n  must_be_manual: []",
        "test_plan:\n  auto_covered: []",
        "test_plan.needs_new_tc",
    ),
    (
        "test_plan:\n  auto_covered:\n    - TC-SYS-001-001\n  needs_new_tc: []\n  must_be_manual: []",
        'test_plan:\n  auto_covered: "TC-SYS-001-001"\n  needs_new_tc: []\n  must_be_manual: []',
        "test_plan.auto_covered",
    ),
    (
        "test_plan:\n  auto_covered:\n    - TC-SYS-001-001\n  needs_new_tc: []\n  must_be_manual: []",
        'test_plan:\n  auto_covered: []\n  needs_new_tc: []\n  must_be_manual: "manual check"',
        "test_plan.must_be_manual",
    ),
])
def test_validate_test_plan_field_errors(tmp_path, replace_old, replace_new, field):
    content = _VALID_FM.replace(replace_old, replace_new)
    path = _write_spec(tmp_path, content)
    errors = validate_spec(path, "CR-001")
    assert any(e["field"] == field for e in errors)


@pytest.mark.parametrize("replace_old,replace_new", [
    pytest.param(
        'design_impact_summary: "Update persistence requirements and tests."\n',
        "",
        id="missing",
    ),
    pytest.param(
        'design_impact_summary: "Update persistence requirements and tests."',
        'design_impact_summary: ""',
        id="empty",
    ),
    pytest.param(
        'design_impact_summary: "Update persistence requirements and tests."',
        "design_impact_summary: 42",
        id="not_string",
    ),
])
def test_validate_design_impact_summary_errors(tmp_path, replace_old, replace_new):
    content = _VALID_FM.replace(replace_old, replace_new)
    path = _write_spec(tmp_path, content)
    errors = validate_spec(path, "CR-001")
    assert any(e["field"] == "design_impact_summary" for e in errors)


def test_validate_missing_test_plan(tmp_path):
    lines = [l for l in _VALID_FM.splitlines()
             if not l.startswith("test_plan") and "auto_covered" not in l
             and "needs_new_tc" not in l and "must_be_manual" not in l
             and "TC-SYS" not in l]
    content = "\n".join(lines)
    path = _write_spec(tmp_path, content)
    errors = validate_spec(path, "CR-001")
    assert any("test_plan" in e["field"] for e in errors)


def test_doc_only_route_rejects_dhf_impact(tmp_path):
    content = _VALID_FM.replace("pipeline_route: standard", "pipeline_route: doc-only")
    path = _write_spec(tmp_path, content)
    errors = validate_spec(path, "CR-001")
    assert any(e["field"] == "affected_items" for e in errors)


def test_doc_only_route_rejects_proposed_new_items(tmp_path):
    content = _VALID_FM.replace("pipeline_route: standard", "pipeline_route: doc-only").replace(
        "proposed_new_items: []",
        "proposed_new_items:\n  - type: SRS\n    title: 'New requirement'",
    )
    path = _write_spec(tmp_path, content)
    errors = validate_spec(path, "CR-001")
    assert any(e["field"] == "proposed_new_items" for e in errors)


def test_test_only_route_rejects_proposed_new_items(tmp_path):
    content = _VALID_FM.replace("pipeline_route: standard", "pipeline_route: test-only").replace(
        "proposed_new_items: []",
        "proposed_new_items:\n  - type: SRS\n    title: 'New requirement'",
    )
    path = _write_spec(tmp_path, content)
    errors = validate_spec(path, "CR-001")
    assert any(e["field"] == "proposed_new_items" for e in errors)


@pytest.mark.parametrize("replace_old,replace_new,expected_fields,expect_no_errors", [
    pytest.param(
        "proposed_new_items: []\n", "", {"proposed_new_items"}, False,
        id="missing",
    ),
    pytest.param(
        "proposed_new_items: []", "proposed_new_items: not-a-list", {"proposed_new_items"}, False,
        id="not_a_list",
    ),
    pytest.param(
        "proposed_new_items: []",
        'proposed_new_items:\n  - type: UNKNOWN\n    title: ""',
        {"proposed_new_items[0].type", "proposed_new_items[0].title"},
        False,
        id="invalid_type_and_empty_title",
    ),
    pytest.param(
        "proposed_new_items: []",
        "proposed_new_items:\n  - title: 'The system shall...'",
        {"proposed_new_items[0].type"},
        False,
        id="missing_type",
    ),
    pytest.param(
        "proposed_new_items: []",
        "proposed_new_items:\n  - type: SRS",
        {"proposed_new_items[0].title"},
        False,
        id="missing_title",
    ),
    pytest.param(
        "proposed_new_items: []",
        "proposed_new_items:\n  - just a string",
        {"proposed_new_items[0]"},
        False,
        id="entry_not_a_dict",
    ),
    pytest.param(
        "proposed_new_items: []",
        "proposed_new_items:\n  - type: SRS\n    title: 'The system shall display...'",
        set(),
        True,
        id="valid_entry_passes",
    ),
    pytest.param(
        "proposed_new_items: []",
        "proposed_new_items:\n  - type: SYS\n    title: 'The system shall display...'\n    parent: 'CRS-001'\n    verification_method: Test",
        set(),
        True,
        id="optional_parent_and_verification_method_pass",
    ),
    pytest.param(
        "proposed_new_items: []",
        "proposed_new_items:\n  - type: SRS\n    title: 'The system shall display...'\n    parent: []",
        {"proposed_new_items[0].parent"},
        False,
        id="parent_must_be_string",
    ),
    pytest.param(
        "proposed_new_items: []",
        "proposed_new_items:\n  - type: SRS\n    title: 'The system shall display...'\n    verification_method: Simulation",
        {"proposed_new_items[0].verification_method"},
        False,
        id="verification_method_must_be_known",
    ),
    pytest.param(
        "proposed_new_items: []",
        "proposed_new_items:\n  - type: SRS\n    title: 'The system shall display...'\n    verification_method: Test",
        {"proposed_new_items[0].verification_method"},
        False,
        id="verification_method_requires_supported_type",
    ),
])
def test_validate_proposed_new_items(tmp_path, replace_old, replace_new, expected_fields, expect_no_errors):
    content = _VALID_FM.replace(replace_old, replace_new)
    path = _write_spec(tmp_path, content)
    errors = validate_spec(path, "CR-001")
    if expect_no_errors:
        assert not any("proposed_new_items" in e["field"] for e in errors)
    else:
        for field in expected_fields:
            matches = [e for e in errors if e["field"] == field]
            assert matches, f"expected error field {field}, got {[e['field'] for e in errors]}"


def test_validate_all_errors_have_fix(tmp_path):
    path = _write_spec(tmp_path, "---\ncr_id: wrong\n---\n")
    errors = validate_spec(path, "CR-001")
    for error in errors:
        assert "fix" in error and error["fix"], f"Error missing fix: {error}"


def test_extract_structured_analysis(tmp_path):
    path = _write_spec(tmp_path, _VALID_FM)
    analysis = extract_structured_analysis(path)
    assert analysis is not None
    assert analysis["disposition"] == "approve"
    assert analysis["pipeline_route"] == "standard"
    assert analysis["decline_rationale"] is None
    assert analysis["affected_items"] == ["SYS-001"]
    assert analysis["proposed_new_items"] == []
    assert analysis["design_impact_summary"] == "Update persistence requirements and tests."
    assert analysis["test_plan"]["auto_covered"] == ["TC-SYS-001-001"]


def test_extract_structured_analysis_maps_legacy_direction_fit(tmp_path):
    content = _VALID_FM.replace("disposition: approve\npipeline_route: standard\n", 'direction_fit: "in-scope"\n')
    path = _write_spec(tmp_path, content)
    analysis = extract_structured_analysis(path)
    assert analysis is not None
    assert analysis["disposition"] == "approve"
    assert analysis["pipeline_route"] == "standard"


def test_extract_structured_analysis_clears_decline_metadata(tmp_path):
    content = (
        "---\n"
        'cr_id: "CR-001"\n'
        "disposition: decline:duplicate\n"
        'decline_rationale: "Already implemented."\n'
        "affected_items:\n"
        "  - SYS-001\n"
        "proposed_new_items:\n"
        "  - type: SRS\n"
        '    title: "Legacy item"\n'
        'design_impact_summary: "Old approval summary."\n'
        "test_plan:\n"
        "  auto_covered:\n"
        "    - TC-SYS-001-001\n"
        "  needs_new_tc: []\n"
        "  must_be_manual: []\n"
        "---\n"
    )
    path = _write_spec(tmp_path, content)
    analysis = extract_structured_analysis(path)
    assert analysis is not None
    assert analysis["affected_items"] == []
    assert analysis["proposed_new_items"] == []
    assert analysis["design_impact_summary"] is None
    assert analysis["test_plan"] is None


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
