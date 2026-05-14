"""Unit tests for medharness.services.design_validation."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from medharness.services.design_validation import validate_generate_dhf


@pytest.fixture
def dhf(tmp_path: Path) -> Path:
    d = tmp_path / "DHF"
    d.mkdir()
    return d


class TestValidateGenerateDhf:
    def test_missing_verification_criteria_on_changed_sys_produces_error(self, dhf):
        with patch("dhfkit.api.validate_schema", return_value={"valid": True, "errors": []}), \
             patch("dhfkit.api.validate_traceability", return_value={"passed": True}), \
             patch("dhfkit.api.list_items", return_value=[
                 {"id": "SYS-001", "type": "SYS", "title": "Existing req",
                  "all_linked_uids": [], "verification_criteria": ""},
             ]):
            errors = validate_generate_dhf(
                "CR-001", dhf, {"created": [], "updated": ["SYS-001"], "deleted": []}
            )
        vc_errors = [e for e in errors if e["field"] == "changed_items[0].verification_criteria"]
        assert len(vc_errors) == 1
        assert "SYS-001" in vc_errors[0]["issue"]

    def test_populated_verification_criteria_on_changed_sys_passes(self, dhf):
        with patch("dhfkit.api.validate_schema", return_value={"valid": True, "errors": []}), \
             patch("dhfkit.api.validate_traceability", return_value={"passed": True}), \
             patch("dhfkit.api.list_items", return_value=[
                 {"id": "SYS-001", "type": "SYS", "title": "Existing req",
                  "all_linked_uids": [], "verification_criteria": "Response < 2s."},
             ]):
            errors = validate_generate_dhf(
                "CR-001", dhf, {"created": [], "updated": ["SYS-001"], "deleted": []}
            )
        assert all("verification_criteria" not in e["field"] for e in errors)

    def test_swdd_change_does_not_require_verification_criteria(self, dhf):
        with patch("dhfkit.api.validate_schema", return_value={"valid": True, "errors": []}), \
             patch("dhfkit.api.validate_traceability", return_value={"passed": True}), \
             patch("dhfkit.api.list_items", return_value=[
                 {"id": "SWDD-001", "type": "SWDD", "title": "Existing design",
                  "all_linked_uids": []},
             ]):
            errors = validate_generate_dhf(
                "CR-001", dhf, {"created": [], "updated": ["SWDD-001"], "deleted": []}
            )
        assert all("verification_criteria" not in e["field"] for e in errors)
