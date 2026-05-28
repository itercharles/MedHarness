"""Unit tests for medharness.services.design_validation."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from medharness.services.design_validation import check_verification_quality, validate_generate_dhf


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


class TestCheckVerificationQuality:
    def _items(self, vc: str, item_id: str = "SRS-001") -> list[dict]:
        return [{"id": item_id, "type": item_id.split("-")[0],
                 "title": "Test", "all_linked_uids": [], "verification_criteria": vc}]

    def test_vague_phrase_returns_warning(self, dhf):
        with patch("dhfkit.api.list_items", return_value=self._items("The feature works correctly.")):
            result = check_verification_quality(dhf, {"created": ["SRS-001"], "updated": []})
        assert len(result) == 1
        assert result[0]["code"] == "vague_verification_criteria"
        assert "SRS-001" in result[0]["message"]
        assert "works correctly" in result[0]["message"]

    def test_measurable_criterion_returns_no_warning(self, dhf):
        vc = "Response latency shall be ≤ 200 ms at the 95th percentile under 1000 concurrent users."
        with patch("dhfkit.api.list_items", return_value=self._items(vc)):
            result = check_verification_quality(dhf, {"created": ["SRS-001"], "updated": []})
        assert result == []

    def test_absent_vc_returns_no_warning(self, dhf):
        with patch("dhfkit.api.list_items", return_value=self._items("")):
            result = check_verification_quality(dhf, {"created": ["SRS-001"], "updated": []})
        assert result == []

    def test_swdd_item_not_checked(self, dhf):
        items = [{"id": "SWDD-001", "type": "SWDD", "title": "Design",
                  "all_linked_uids": [], "verification_criteria": "behaves as expected"}]
        with patch("dhfkit.api.list_items", return_value=items):
            result = check_verification_quality(dhf, {"created": ["SWDD-001"], "updated": []})
        assert result == []

    def test_only_changed_items_are_checked(self, dhf):
        items = [
            {"id": "SRS-001", "type": "SRS", "title": "A",
             "all_linked_uids": [], "verification_criteria": "works correctly"},
            {"id": "SRS-002", "type": "SRS", "title": "B",
             "all_linked_uids": [], "verification_criteria": "works correctly"},
        ]
        with patch("dhfkit.api.list_items", return_value=items):
            result = check_verification_quality(dhf, {"created": ["SRS-001"], "updated": []})
        assert len(result) == 1
        assert result[0]["field"] == "SRS-001.verification_criteria"

    def test_updated_items_also_checked(self, dhf):
        with patch("dhfkit.api.list_items", return_value=self._items("behaves as expected")):
            result = check_verification_quality(dhf, {"created": [], "updated": ["SRS-001"]})
        assert len(result) == 1

    def test_all_vague_phrases_detected(self, dhf):
        vague_phrases = [
            "The system behaves as expected under load.",
            "Login functions correctly after session expiry.",
            "The module operates correctly.",
            "This should work for all users.",
        ]
        for phrase in vague_phrases:
            with patch("dhfkit.api.list_items", return_value=self._items(phrase)):
                result = check_verification_quality(dhf, {"created": ["SRS-001"], "updated": []})
            assert len(result) == 1, f"Expected warning for: {phrase!r}"

    def test_crs_and_sys_items_also_checked(self, dhf):
        for item_id in ("CRS-001", "SYS-001"):
            with patch("dhfkit.api.list_items", return_value=self._items("functions properly", item_id)):
                result = check_verification_quality(dhf, {"created": [item_id], "updated": []})
            assert len(result) == 1, f"Expected warning for {item_id}"

    def test_duplicate_item_ids_not_double_counted(self, dhf):
        with patch("dhfkit.api.list_items", return_value=self._items("works correctly")):
            result = check_verification_quality(
                dhf, {"created": ["SRS-001"], "updated": ["SRS-001"]}
            )
        assert len(result) == 1
