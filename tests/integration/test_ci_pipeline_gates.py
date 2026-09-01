"""Golden integration tests for CI pipeline gate commands.

Covers the validation surface that does NOT require LLM calls:
  - verify dhf (ci_structural_gate): schema, traceability, structured reporting
  - verify branch: DHF change detection, spec item existence
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
# Shared fixtures
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


@pytest.fixture(scope="module")
def dhf_validate_result(dhf):
    """Run verify dhf once and share the parsed result across the test class."""
    r = subprocess.run(
        [sys.executable, "-m", "medharness", "verify", "dhf", "--dhf", str(dhf / "DHF")],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    assert r.returncode in (0, 1), f"verify dhf crashed:\n{r.stderr}"
    return json.loads(r.stdout)


def _medharness(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "medharness"] + list(args),
        capture_output=True, text=True, cwd=REPO_ROOT,
    )


# ---------------------------------------------------------------------------
# verify dhf — ci_structural_gate structured output
# ---------------------------------------------------------------------------

class TestCiStructuralGate:
    """Verify that verify dhf returns the expected structured fields."""

    def test_schema_passes_on_clean_dhf(self, dhf_validate_result):
        result = dhf_validate_result
        assert "passed" in result
        assert "results" in result["details"]
        assert "schema" in result["details"]["results"]
        assert result["details"]["results"]["schema"]["passed"], "Schema should pass on fresh scaffold"

    def test_traceability_result_shape(self, dhf_validate_result):
        tr = dhf_validate_result["details"]["results"].get("traceability", {})
        assert "passed" in tr
        assert "required" in tr
        assert "coverage" in tr

    def test_structured_coverage_gaps_key_present(self, dhf_validate_result):
        assert "coverage_gaps" in dhf_validate_result["details"]["results"], (
            "verify dhf must return structured coverage_gaps list"
        )
        assert isinstance(dhf_validate_result["details"]["results"]["coverage_gaps"], list)

    def test_structured_orphans_key_present(self, dhf_validate_result):
        assert "orphans" in dhf_validate_result["details"]["results"]
        assert isinstance(dhf_validate_result["details"]["results"]["orphans"], list)

    def test_structured_verification_gaps_key_present(self, dhf_validate_result):
        assert "verification_gaps" in dhf_validate_result["details"]["results"]
        vgaps = dhf_validate_result["details"]["results"]["verification_gaps"]
        assert isinstance(vgaps, list)
        for gap in vgaps:
            assert "id" in gap
            assert "type" in gap
            assert "issue" in gap

    def test_coverage_gap_entries_have_required_keys(self, dhf_validate_result):
        for gap in dhf_validate_result["details"]["results"]["coverage_gaps"]:
            assert "parent_type" in gap
            assert "child_type" in gap
            assert "uncovered" in gap

    def test_structured_keys_present_regardless_of_traceability_flag(self, dhf):
        """coverage_gaps, orphans, verification_gaps must be present even when
        traceability is disabled, so machine consumers can always rely on them."""
        r = _medharness(
            "verify", "dhf", "--dhf", str(dhf / "DHF"),
            "--no-run-traceability",
        )
        assert r.returncode in (0, 1), f"crashed:\n{r.stderr}"
        result = json.loads(r.stdout)
        assert "coverage_gaps" in result["details"]["results"]
        assert "orphans" in result["details"]["results"]
        assert "verification_gaps" in result["details"]["results"]


# ---------------------------------------------------------------------------
# verify branch — change detection and spec item existence
# ---------------------------------------------------------------------------

class TestValidateBranch:
    """Verify validate-branch catches missing DHF changes and bad spec items."""

    def test_clean_branch_has_no_dhf_changes(self, dhf):
        """A branch with no commits since HEAD has no DHF changes."""
        r = _medharness(
            "--dhf", str(dhf / "DHF"),
            "verify", "branch",
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
            "verify", "branch",
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
            "verify", "branch",
            "--cr", "CR-001",
            "--since-ref", "HEAD",
        )
        result = json.loads(r.stdout)
        assert result.get("cr_id") == "CR-001"

    def test_since_ref_is_echoed(self, dhf):
        r = _medharness(
            "--dhf", str(dhf / "DHF"),
            "verify", "branch",
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

    def test_cascade_no_error_when_child_links_back(self):
        from medharness.services.design_validation import _validate_cascade_completeness

        by_id = {
            "CRS-001": {"id": "CRS-001"},
            "SYS-001": {"id": "SYS-001", "derives_from": ["CRS-001"]},
        }
        errors = _validate_cascade_completeness(["CRS-001"], by_id)
        assert not any(e["field"].startswith("cascade.CRS-001") for e in errors)

    def test_cascade_error_when_child_missing(self):
        from medharness.services.design_validation import _validate_cascade_completeness

        by_id = {"CRS-001": {"id": "CRS-001"}}
        errors = _validate_cascade_completeness(["CRS-001"], by_id)
        assert any(e["field"].startswith("cascade.CRS-001") for e in errors)

    def test_cascade_no_error_for_leaf_types(self):
        """SWDD, RISK, RCM etc. have no required children — should never flag."""
        from medharness.services.design_validation import _validate_cascade_completeness

        by_id = {
            "SWDD-001": {"id": "SWDD-001"},
            "RISK-001": {"id": "RISK-001"},
        }
        errors = _validate_cascade_completeness(["SWDD-001", "RISK-001"], by_id)
        assert errors == []

    def test_cascade_not_triggered_for_updated_items(self):
        """Updating an existing parent must NOT trigger the cascade check."""
        from medharness.services.design_validation import _validate_cascade_completeness

        by_id = {"SYS-001": {"id": "SYS-001"}}
        # SYS-001 is not in created_ids
        errors = _validate_cascade_completeness([], by_id)
        assert errors == []

    def test_cascade_uses_link_fields_not_all_linked_uids(self):
        """Cascade check must work from raw link fields, not the enriched all_linked_uids."""
        from medharness.services.design_validation import _validate_cascade_completeness

        by_id = {
            "SRS-001": {"id": "SRS-001"},
            "SWDD-001": {"id": "SWDD-001", "implements": ["SRS-001"]},
        }
        errors = _validate_cascade_completeness(["SRS-001"], by_id)
        assert not any(e["field"].startswith("cascade.SRS-001") for e in errors)

    def test_cascade_finds_child_anywhere_in_dhf(self):
        """Child found in by_id (full DHF) but NOT in the current run's changed set
        must still mark the parent as covered."""
        from medharness.services.design_validation import _validate_cascade_completeness

        # SYS-099 exists in DHF (pre-existing, not "changed") but links to new CRS-010
        by_id = {
            "CRS-010": {"id": "CRS-010"},
            "SYS-099": {"id": "SYS-099", "derives_from": ["CRS-010"]},
        }
        # Only CRS-010 is in created_ids; SYS-099 is a pre-existing item that was
        # updated in the same run and already persisted to the DHF
        errors = _validate_cascade_completeness(["CRS-010"], by_id)
        assert not any(e["field"].startswith("cascade.CRS-010") for e in errors)

    def test_cascade_error_has_fix_hint(self):
        from medharness.services.design_validation import _validate_cascade_completeness

        by_id = {"SYS-001": {"id": "SYS-001"}}
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
