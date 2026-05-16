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
)

# ── Stable contracts (what JSON consumers may depend on) ─────────────────────

# Union of all keys the response *may* contain. Use this to keep the surface
# area honest — reviewers can see the full schema in one place.
COMMON_KEYS = {
    "cr_id",
    "stage",
    "outcome",
    "summary",
    "timing",
    "inputs",
    "progress",
    "steps",
    "artifacts",
    "diagnostics",
    "warnings",
    "errors",
}

# Removed in v0.3.5 — kept here as an explicit regression list. These keys
# always returned null / [] in earlier versions and were dropped because no
# consumer could derive value from them. If a future change re-introduces
# any of them, this test will surface the decision for review.
REMOVED_LEGACY_KEYS = {
    "items_created", "items_updated", "files_written",
    "status", "corrections", "validation", "started_at", "elapsed_ms",
    "spec_path", "analysis", "spec_json_path", "items_changed", "files_changed",
}

STAGE_VALUES = {"develop", "generate_dhf"}
OUTCOME_VALUES = {"ok", "corrected", "completed_with_errors", "tool_error"}


def _change_bucket_keys() -> set[str]:
    return {"created", "updated", "deleted"}


@pytest.fixture
def dhf(tmp_path: Path) -> Path:
    d = tmp_path / "DHF"
    d.mkdir()
    return d


def _empty_diff() -> MagicMock:
    return MagicMock(stdout="", returncode=0)


# ── generate_code ────────────────────────────────────────────────────────────

class TestGenerateCodeContract:
    @pytest.fixture(autouse=True)
    def stub_session(self, monkeypatch):
        monkeypatch.setattr("medharness.services.cr_generation.get_session", lambda pr: "")
        monkeypatch.setattr("medharness.services.cr_generation.put_session", lambda pr, sid: None)

    def test_keys_present_and_no_legacy_leak(self, dhf):
        with patch("medharness.services.cr_generation._run_claude",
                   return_value=(0, "", "")), \
             patch("medharness.services.code_validation.validate_code",
                   return_value=[]), \
             patch("subprocess.run", return_value=_empty_diff()):
            result = generate_code("CR-200", dhf)
        assert COMMON_KEYS <= result.keys(), (
            f"missing keys: {COMMON_KEYS - result.keys()}"
        )
        assert REMOVED_LEGACY_KEYS.isdisjoint(result.keys()), (
            f"legacy key leaked back: {REMOVED_LEGACY_KEYS & result.keys()}"
        )

    def test_value_domains(self, dhf):
        with patch("medharness.services.cr_generation._run_claude",
                   return_value=(0, "", "")), \
             patch("medharness.services.code_validation.validate_code",
                   return_value=[]), \
             patch("subprocess.run", return_value=_empty_diff()):
            result = generate_code("CR-200", dhf)
        assert result["stage"] == "develop"
        assert result["outcome"] in OUTCOME_VALUES

    def test_files_changed_shape(self, dhf):
        with patch("medharness.services.cr_generation._run_claude",
                   return_value=(0, "", "")), \
             patch("medharness.services.code_validation.validate_code",
                   return_value=[]), \
             patch("subprocess.run", return_value=_empty_diff()):
            result = generate_code("CR-200", dhf)
        files = result["artifacts"]["files_changed"]
        assert set(files.keys()) == _change_bucket_keys()
        for bucket in files.values():
            assert isinstance(bucket, list)


# ── JSON-serializability — the contract is JSON, not Python dicts ────────────

class TestResponseIsJsonSerializable:
    @pytest.fixture(autouse=True)
    def stub_session(self, monkeypatch):
        monkeypatch.setattr("medharness.services.cr_generation.get_session", lambda pr: "")
        monkeypatch.setattr("medharness.services.cr_generation.put_session", lambda pr, sid: None)

    def test_code_response_is_json(self, dhf):
        import json
        with patch("medharness.services.cr_generation._run_claude",
                   return_value=(0, "", "")), \
             patch("medharness.services.code_validation.validate_code",
                   return_value=[]), \
             patch("subprocess.run", return_value=_empty_diff()):
            result = generate_code("CR-301", dhf)
        json.dumps(result)
