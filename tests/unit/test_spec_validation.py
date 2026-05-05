"""Tests for medharness.services.spec_validation."""

import pytest
from pathlib import Path
from medharness.services.spec_validation import parse_spec_frontmatter, validate_spec


_VALID_FM = """\
---
cr_id: "CR-001"
direction_fit: "in-scope"
affected_items:
  - SYS-001
proposed_new_items: []
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
    content = _VALID_FM.replace("direction_fit: \"in-scope\"\n", "")
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


def test_validate_test_plan_missing_keys(tmp_path):
    content = _VALID_FM.replace(
        "test_plan:\n  auto_covered:\n    - TC-SYS-001-001\n  needs_new_tc: []\n  must_be_manual: []",
        "test_plan:\n  auto_covered: []"
    )
    path = _write_spec(tmp_path, content)
    errors = validate_spec(path, "CR-001")
    missing_keys = {e["field"] for e in errors}
    assert "test_plan.needs_new_tc" in missing_keys
    assert "test_plan.must_be_manual" in missing_keys


def test_validate_all_errors_have_fix(tmp_path):
    path = _write_spec(tmp_path, "---\ncr_id: wrong\n---\n")
    errors = validate_spec(path, "CR-001")
    for e in errors:
        assert "fix" in e and e["fix"], f"Error missing fix: {e}"
