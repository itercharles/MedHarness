"""Schema lock-in tests for the generate-* response payload.

These tests are deliberately strict and exhaustive — their job is to fail
loudly if a key is renamed, removed, or re-added. The unit tests in
``test_cr_generation.py`` cover *behavior*; this file covers the
*contract* the CLI advertises to JSON consumers (workflow steps that
read ``ci design-cr`` stdout, dashboards, PR-comment bots, etc.).

If you intentionally change the contract, update these assertions and
the CHANGELOG entry in lock-step.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from medharness.services.cr_generation import (
    generate_code,
    generate_design,
    generate_spec,
)

# ── Stable contracts (what JSON consumers may depend on) ─────────────────────

# Union of all keys the response *may* contain. Use this to keep the surface
# area honest — reviewers can see the full schema in one place.
COMMON_KEYS = {
    "cr_id",
    "stage",
    "status",
    "corrections",
    "validation",
    "errors",
    "started_at",
    "elapsed_ms",
}
SPEC_EXTRA_KEYS = {"spec_path", "analysis", "spec_json_path"}
DESIGN_EXTRA_KEYS = {"items_changed"}
DEVELOP_EXTRA_KEYS = {"files_changed"}

# Removed in v0.3.5 — kept here as an explicit regression list. These keys
# always returned null / [] in earlier versions and were dropped because no
# consumer could derive value from them. If a future change re-introduces
# any of them, this test will surface the decision for review.
REMOVED_LEGACY_KEYS = {"items_created", "items_updated", "files_written"}

# Allowed values — string-match consumers should be checked against these.
STAGE_VALUES = {"spec", "design", "develop"}
STATUS_VALUES = {"ok", "completed_with_errors"}
VALIDATION_VALUES_SPEC = {"passed", "corrected"}
VALIDATION_VALUES_DESIGN_DEVELOP = {"passed", "residual_errors"}


def _change_bucket_keys() -> set[str]:
    return {"created", "updated", "deleted"}


@pytest.fixture
def dhf(tmp_path: Path) -> Path:
    d = tmp_path / "DHF"
    d.mkdir()
    return d


def _empty_diff() -> MagicMock:
    return MagicMock(stdout="", returncode=0)


# ── generate_spec ────────────────────────────────────────────────────────────

class TestGenerateSpecContract:
    def _spec(self, dhf: Path, cr_id: str = "CR-001") -> Path:
        spec_path = dhf.parent / "docs" / "cr-specs" / f"{cr_id}-Spec.md"
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        spec_path.write_text(
            f'---\ncr_id: "{cr_id}"\ndirection_fit: "in-scope"\n'
            'affected_items: []\nproposed_new_items: []\n'
            'design_impact_summary: "Test summary."\n'
            'test_plan:\n  auto_covered: []\n'
            '  needs_new_tc: []\n  must_be_manual: []\n---\n',
            encoding="utf-8",
        )
        return spec_path

    def test_keys_present_and_no_legacy_leak(self, dhf):
        self._spec(dhf)
        with patch("medharness.services.cr_generation._run_claude",
                   return_value=(0, "")):
            result = generate_spec("CR-001", dhf)
        assert COMMON_KEYS | SPEC_EXTRA_KEYS <= result.keys(), (
            f"missing keys: {(COMMON_KEYS | SPEC_EXTRA_KEYS) - result.keys()}"
        )
        assert REMOVED_LEGACY_KEYS.isdisjoint(result.keys()), (
            f"legacy key leaked back: {REMOVED_LEGACY_KEYS & result.keys()}"
        )
        # Schema typing
        assert isinstance(result["errors"], list)
        assert isinstance(result["corrections"], int)
        assert isinstance(result["elapsed_ms"], int)
        assert isinstance(result["started_at"], str)
        assert isinstance(result["spec_path"], str)
        assert isinstance(result["analysis"], dict)
        assert isinstance(result["spec_json_path"], str)

    def test_value_domains(self, dhf):
        self._spec(dhf)
        with patch("medharness.services.cr_generation._run_claude",
                   return_value=(0, "")):
            result = generate_spec("CR-001", dhf)
        assert result["stage"] == "spec"
        assert result["status"] in STATUS_VALUES
        assert result["validation"] in VALIDATION_VALUES_SPEC
        assert set(result["analysis"]) == {
            "direction_fit",
            "affected_items",
            "proposed_new_items",
            "design_impact_summary",
            "test_plan",
        }


# ── generate_design ──────────────────────────────────────────────────────────

class TestGenerateDesignContract:
    def test_keys_present_and_no_legacy_leak(self, dhf):
        with patch("medharness.services.cr_generation._run_claude",
                   return_value=(0, "")), \
             patch("medharness.services.design_validation.validate_design",
                   return_value=[]), \
             patch("subprocess.run", return_value=_empty_diff()):
            result = generate_design("CR-100", dhf)
        assert COMMON_KEYS | DESIGN_EXTRA_KEYS <= result.keys(), (
            f"missing keys: {(COMMON_KEYS | DESIGN_EXTRA_KEYS) - result.keys()}"
        )
        assert REMOVED_LEGACY_KEYS.isdisjoint(result.keys()), (
            f"legacy key leaked back: {REMOVED_LEGACY_KEYS & result.keys()}"
        )

    def test_value_domains(self, dhf):
        with patch("medharness.services.cr_generation._run_claude",
                   return_value=(0, "")), \
             patch("medharness.services.design_validation.validate_design",
                   return_value=[]), \
             patch("subprocess.run", return_value=_empty_diff()):
            result = generate_design("CR-100", dhf)
        assert result["stage"] == "design"
        assert result["status"] in STATUS_VALUES
        assert result["validation"] in VALIDATION_VALUES_DESIGN_DEVELOP

    def test_items_changed_shape(self, dhf):
        with patch("medharness.services.cr_generation._run_claude",
                   return_value=(0, "")), \
             patch("medharness.services.design_validation.validate_design",
                   return_value=[]), \
             patch("subprocess.run", return_value=_empty_diff()):
            result = generate_design("CR-100", dhf)
        items = result["items_changed"]
        assert set(items.keys()) == _change_bucket_keys()
        for bucket in items.values():
            assert isinstance(bucket, list)

    def test_completed_with_errors_when_residual(self, dhf):
        residual = [{"field": "schema", "issue": "x", "fix": "y"}]
        with patch("medharness.services.cr_generation._run_claude",
                   return_value=(0, "")), \
             patch("medharness.services.design_validation.validate_design",
                   side_effect=[residual, residual]), \
             patch("subprocess.run", return_value=_empty_diff()):
            result = generate_design("CR-100", dhf)
        assert result["status"] == "completed_with_errors"
        assert result["validation"] == "residual_errors"
        assert result["errors"] == residual


# ── generate_code ────────────────────────────────────────────────────────────

class TestGenerateCodeContract:
    def test_keys_present_and_no_legacy_leak(self, dhf):
        with patch("medharness.services.cr_generation._run_claude",
                   return_value=(0, "")), \
             patch("medharness.services.code_validation.validate_code",
                   return_value=[]), \
             patch("subprocess.run", return_value=_empty_diff()):
            result = generate_code("CR-200", dhf)
        assert COMMON_KEYS | DEVELOP_EXTRA_KEYS <= result.keys(), (
            f"missing keys: {(COMMON_KEYS | DEVELOP_EXTRA_KEYS) - result.keys()}"
        )
        assert REMOVED_LEGACY_KEYS.isdisjoint(result.keys()), (
            f"legacy key leaked back: {REMOVED_LEGACY_KEYS & result.keys()}"
        )

    def test_value_domains(self, dhf):
        with patch("medharness.services.cr_generation._run_claude",
                   return_value=(0, "")), \
             patch("medharness.services.code_validation.validate_code",
                   return_value=[]), \
             patch("subprocess.run", return_value=_empty_diff()):
            result = generate_code("CR-200", dhf)
        assert result["stage"] == "develop"
        assert result["status"] in STATUS_VALUES
        assert result["validation"] in VALIDATION_VALUES_DESIGN_DEVELOP

    def test_files_changed_shape(self, dhf):
        with patch("medharness.services.cr_generation._run_claude",
                   return_value=(0, "")), \
             patch("medharness.services.code_validation.validate_code",
                   return_value=[]), \
             patch("subprocess.run", return_value=_empty_diff()):
            result = generate_code("CR-200", dhf)
        files = result["files_changed"]
        assert set(files.keys()) == _change_bucket_keys()
        for bucket in files.values():
            assert isinstance(bucket, list)


# ── JSON-serializability — the contract is JSON, not Python dicts ────────────

class TestResponseIsJsonSerializable:
    def test_design_response_is_json(self, dhf):
        import json
        with patch("medharness.services.cr_generation._run_claude",
                   return_value=(0, "")), \
             patch("medharness.services.design_validation.validate_design",
                   return_value=[]), \
             patch("subprocess.run", return_value=_empty_diff()):
            result = generate_design("CR-300", dhf)
        # If this raises, a non-JSON-safe value (e.g. a Path) leaked into the
        # response and would crash `click.echo(json.dumps(result))`.
        json.dumps(result)

    def test_code_response_is_json(self, dhf):
        import json
        with patch("medharness.services.cr_generation._run_claude",
                   return_value=(0, "")), \
             patch("medharness.services.code_validation.validate_code",
                   return_value=[]), \
             patch("subprocess.run", return_value=_empty_diff()):
            result = generate_code("CR-301", dhf)
        json.dumps(result)
