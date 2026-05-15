"""Golden integration tests for CI pipeline gate commands.

Covers the validation surface that does NOT require LLM calls:
  - ci dhf-validate (ci_structural_gate): schema, traceability, structured reporting
  - ci validate-branch: DHF change detection, spec item existence
  - validate_generate_dhf: verification_criteria, V-model cascade completeness
  - ItemType display_name / code contract

All operations run against a real scaffolded DHF fixture with a git repo.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from medharness.workflows.init import _scaffold_dhf, _replace_placeholders

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def dhf():
    """Scaffold a DHF with an initialised git repo for all gate tests."""
    with tempfile.TemporaryDirectory() as tmp:
        dhf_dir = Path(tmp) / "gate-dhf"
        _scaffold_dhf(dhf_dir)
        _replace_placeholders(dhf_dir, "Gate Test Project")
        for cmd in [
            ["git", "init", "-b", "main", str(dhf_dir)],
            ["git", "-C", str(dhf_dir), "config", "user.email", "gate@test.local"],
            ["git", "-C", str(dhf_dir), "config", "user.name", "Gate Test"],
            ["git", "-C", str(dhf_dir), "add", "-A"],
            ["git", "-C", str(dhf_dir), "commit", "-m", "init"],
        ]:
            subprocess.run(cmd, capture_output=True, check=True)
        yield dhf_dir


def _medharness(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "medharness"] + list(args),
        capture_output=True, text=True, cwd=REPO_ROOT,
    )


def _dhf(dhf_root: str, *args: str) -> subprocess.CompletedProcess:
    return _medharness("--dhf", dhf_root, "dhf", *args)


# ---------------------------------------------------------------------------
# ci dhf-validate — ci_structural_gate structured output
# ---------------------------------------------------------------------------

class TestCiStructuralGate:
    """Verify that ci dhf-validate returns the expected structured fields."""

    def test_schema_passes_on_clean_dhf(self, dhf):
        r = _medharness("ci", "dhf-validate", "--dhf", str(dhf / "DHF"))
        assert r.returncode in (0, 1), f"crashed:\n{r.stderr}"
        result = json.loads(r.stdout)
        assert "passed" in result
        assert "results" in result
        assert "schema" in result["results"]
        assert result["results"]["schema"]["passed"], (
            f"Schema should pass on fresh scaffold:\n{r.stderr}"
        )

    def test_traceability_result_shape(self, dhf):
        r = _medharness("ci", "dhf-validate", "--dhf", str(dhf / "DHF"))
        result = json.loads(r.stdout)
        tr = result["results"].get("traceability", {})
        assert "passed" in tr
        assert "required" in tr
        assert "coverage" in tr

    def test_structured_coverage_gaps_key_present(self, dhf):
        r = _medharness("ci", "dhf-validate", "--dhf", str(dhf / "DHF"))
        result = json.loads(r.stdout)
        assert "coverage_gaps" in result["results"], (
            "ci dhf-validate must return structured coverage_gaps list"
        )
        assert isinstance(result["results"]["coverage_gaps"], list)

    def test_structured_orphans_key_present(self, dhf):
        r = _medharness("ci", "dhf-validate", "--dhf", str(dhf / "DHF"))
        result = json.loads(r.stdout)
        assert "orphans" in result["results"]
        assert isinstance(result["results"]["orphans"], list)

    def test_structured_verification_gaps_key_present(self, dhf):
        r = _medharness("ci", "dhf-validate", "--dhf", str(dhf / "DHF"))
        result = json.loads(r.stdout)
        assert "verification_gaps" in result["results"]
        vgaps = result["results"]["verification_gaps"]
        assert isinstance(vgaps, list)
        for gap in vgaps:
            assert "id" in gap
            assert "type" in gap
            assert "issue" in gap

    def test_coverage_gap_entries_have_required_keys(self, dhf):
        r = _medharness("ci", "dhf-validate", "--dhf", str(dhf / "DHF"))
        result = json.loads(r.stdout)
        for gap in result["results"]["coverage_gaps"]:
            assert "parent_type" in gap
            assert "child_type" in gap
            assert "uncovered" in gap


# ---------------------------------------------------------------------------
# ci validate-branch — change detection and spec item existence
# ---------------------------------------------------------------------------

class TestValidateBranch:
    """Verify validate-branch catches missing DHF changes and bad spec items."""

    def test_clean_branch_has_no_dhf_changes(self, dhf):
        """A branch with no commits since HEAD has no DHF changes."""
        r = _medharness(
            "--dhf", str(dhf / "DHF"),
            "ci", "validate-branch",
            "--cr", "CR-001",
            "--since-ref", "HEAD",
        )
        result = json.loads(r.stdout)
        assert not result["passed"], (
            "Branch with no changes since HEAD should fail the DHF-change check"
        )
        fields = [e["field"] for e in result["errors"]]
        assert "dhf_branch" in fields

    def test_result_includes_dhf_item_changes(self, dhf):
        r = _medharness(
            "--dhf", str(dhf / "DHF"),
            "ci", "validate-branch",
            "--cr", "CR-001",
            "--since-ref", "HEAD",
        )
        result = json.loads(r.stdout)
        assert "dhf_item_changes" in result
        changes = result["dhf_item_changes"]
        assert "created" in changes and "updated" in changes and "deleted" in changes

    def test_result_includes_cr_id(self, dhf):
        r = _medharness(
            "--dhf", str(dhf / "DHF"),
            "ci", "validate-branch",
            "--cr", "CR-001",
            "--since-ref", "HEAD",
        )
        result = json.loads(r.stdout)
        assert result.get("cr_id") == "CR-001"

    def test_since_ref_is_echoed(self, dhf):
        r = _medharness(
            "--dhf", str(dhf / "DHF"),
            "ci", "validate-branch",
            "--cr", "CR-001",
            "--since-ref", "HEAD",
        )
        result = json.loads(r.stdout)
        assert result.get("since_ref") == "HEAD"


# ---------------------------------------------------------------------------
# validate_generate_dhf — V-model cascade completeness
# ---------------------------------------------------------------------------

class TestValidateGenerateDhfCascade:
    """Unit-level tests for the cascade completeness check."""

    def test_cascade_no_error_when_child_present(self):
        from medharness.services.design_validation import _validate_cascade_completeness

        by_id = {
            "CRS-001": {"id": "CRS-001", "all_linked_uids": []},
            "SYS-001": {"id": "SYS-001", "all_linked_uids": ["CRS-001"]},
        }
        errors = _validate_cascade_completeness(["CRS-001", "SYS-001"], by_id)
        # CRS-001 has SYS-001 linking back → no cascade error
        assert not any(e["field"].startswith("cascade.CRS-001") for e in errors)

    def test_cascade_error_when_child_missing(self):
        from medharness.services.design_validation import _validate_cascade_completeness

        by_id = {
            "CRS-001": {"id": "CRS-001", "all_linked_uids": []},
        }
        errors = _validate_cascade_completeness(["CRS-001"], by_id)
        assert any(e["field"].startswith("cascade.CRS-001") for e in errors)

    def test_cascade_no_error_for_leaf_types(self):
        """SWDD, RISK, RCM etc. have no required children — should never flag."""
        from medharness.services.design_validation import _validate_cascade_completeness

        by_id = {
            "SWDD-001": {"id": "SWDD-001", "all_linked_uids": []},
            "RISK-001": {"id": "RISK-001", "all_linked_uids": []},
        }
        errors = _validate_cascade_completeness(["SWDD-001", "RISK-001"], by_id)
        assert errors == []

    def test_cascade_error_has_fix_hint(self):
        from medharness.services.design_validation import _validate_cascade_completeness

        by_id = {"SYS-001": {"id": "SYS-001", "all_linked_uids": []}}
        errors = _validate_cascade_completeness(["SYS-001"], by_id)
        assert errors
        assert "fix" in errors[0]
        assert "SRS" in errors[0]["fix"] or "SYSARCH" in errors[0]["fix"]


# ---------------------------------------------------------------------------
# ItemType display_name / code contract
# ---------------------------------------------------------------------------

class TestItemTypeDisplayNameContract:
    """Verify adapter returns display_name (not name) and code is separate."""

    def test_local_adapter_returns_display_name_key(self, dhf):
        from dhfkit.local_adapter import LocalDHFAdapter
        adapter = LocalDHFAdapter(dhf / "DHF")
        types = adapter.list_item_types()
        assert types, "expect at least one item type"
        for t in types:
            assert "display_name" in t, f"item type {t.get('code')} missing display_name key"
            assert "name" not in t, f"item type {t.get('code')} must not use ambiguous 'name' key"

    def test_display_name_is_human_readable(self, dhf):
        from dhfkit.local_adapter import LocalDHFAdapter
        adapter = LocalDHFAdapter(dhf / "DHF")
        t = adapter.get_item_type("SYS-")
        assert t is not None
        assert t["display_name"] == "System Requirement"
        assert t["code"] == "SYS"

    def test_display_name_differs_from_code(self, dhf):
        from dhfkit.local_adapter import LocalDHFAdapter
        adapter = LocalDHFAdapter(dhf / "DHF")
        for t in adapter.list_item_types():
            assert t["display_name"] != t["code"], (
                f"display_name should be human-readable, not the code ({t['code']})"
            )
