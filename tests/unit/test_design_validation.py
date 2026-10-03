"""Unit tests for medharness.services.design_validation."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from medharness.services.design_validation import check_verification_quality, validate_generate_dhf


@pytest.fixture
def dhf(tmp_path: Path) -> Path:
    """The default config, so the verifiable types come from where they live;
    the items themselves are patched per test."""
    import shutil

    from dhfkit.paths import DEFAULTS_DIR as _TEMPLATES_DIR

    d = tmp_path / "DHF"
    shutil.copytree(_TEMPLATES_DIR / "config", d / "config")
    (d / "items").mkdir()
    return d


class TestValidateGenerateDhf:
    """Scoped to the changed-item checks.

    `_check_cr_workflow_fields` is stubbed out here: these fixtures carry no CR
    item, and what it reports has its own tests in
    test_plan_leaves_what_closure_needs.py.
    """

    @patch("medharness.services.design_validation._check_cr_workflow_fields", return_value=[])
    def test_missing_verification_criteria_on_changed_sys_produces_error(self, _cr, dhf):
        with patch("dhfkit.api.validate_schema", return_value={"valid": True, "errors": []}), \
             patch("medharness.services.design_validation.analyse", return_value={"passed": True}), \
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

    @patch("medharness.services.design_validation._check_cr_workflow_fields", return_value=[])
    def test_populated_verification_criteria_on_changed_sys_passes(self, _cr, dhf):
        with patch("dhfkit.api.validate_schema", return_value={"valid": True, "errors": []}), \
             patch("medharness.services.design_validation.analyse", return_value={"passed": True}), \
             patch("dhfkit.api.list_items", return_value=[
                 {"id": "SYS-001", "type": "SYS", "title": "Existing req",
                  "all_linked_uids": [], "verification_criteria": "Response < 2s."},
             ]):
            errors = validate_generate_dhf(
                "CR-001", dhf, {"created": [], "updated": ["SYS-001"], "deleted": []}
            )
        assert all("verification_criteria" not in e["field"] for e in errors)

    @patch("medharness.services.design_validation._check_cr_workflow_fields", return_value=[])
    def test_swdd_change_does_not_require_verification_criteria(self, _cr, dhf):
        with patch("dhfkit.api.validate_schema", return_value={"valid": True, "errors": []}), \
             patch("medharness.services.design_validation.analyse", return_value={"passed": True}), \
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


class TestImpactAnalysisShape:
    """The judge of a CR's `impact_analysis` form: many branches, so each is enumerated here."""

    NINE = ("product", "requirements", "architecture", "risk", "soup",
            "test", "regulatory", "security", "usability")

    def _record(self, **overrides) -> dict:
        record = {
            "assumptions": ["a reading of the issue"],
            "anchors": [{"id": "SRS-001", "evidence": "tests/a.spec.ts @links:SRS-001"}],
            "unchanged": [{"id": "SYS-001", "reason": "still holds"}],
            "created": [],
            "dimensions": [{"dimension": d, "verdict": "not_required", "reason": "no effect", "items": []}
                           for d in self.NINE],
        }
        record.update(overrides)
        return record

    def _fields(self, record) -> list[str]:
        from medharness.services.design_validation import impact_analysis_shape_errors

        return [e["field"] for e in impact_analysis_shape_errors("CR-001", record)]

    def test_a_complete_record_is_clean(self):
        assert self._fields(self._record()) == []

    @pytest.mark.parametrize("record", [None, "text", [], 0])
    def test_a_record_that_is_not_a_mapping_is_one_error(self, record):
        assert self._fields(record) == ["impact_analysis"]

    @pytest.mark.parametrize("key", ["assumptions", "anchors", "unchanged", "created", "dimensions"])
    def test_a_missing_key_is_named(self, key):
        record = self._record()
        del record[key]
        assert f"impact_analysis.{key}" in self._fields(record)

    def test_a_key_that_is_not_a_list_is_named(self):
        assert "impact_analysis.anchors" in self._fields(self._record(anchors={"id": "SRS-001"}))

    def test_an_assumption_must_be_text(self):
        assert self._fields(self._record(assumptions=["ok", ""])) == ["impact_analysis.assumptions[1]"]

    @pytest.mark.parametrize("key", ["anchors", "unchanged", "created"])
    @pytest.mark.parametrize("entry", ["SRS-001", {"reason": "no id"}, {"id": ""}])
    def test_an_entry_needs_an_id(self, key, entry):
        assert self._fields(self._record(**{key: [entry]})) == [f"impact_analysis.{key}[0]"]

    def test_a_missing_dimension_is_named(self):
        record = self._record(dimensions=self._record()["dimensions"][:-1])
        errors = self._issues(record)
        assert len(errors) == 1 and "'usability' appears 0 times" in errors[0]

    def test_a_repeated_dimension_is_named(self):
        dims = self._record()["dimensions"]
        errors = self._issues(self._record(dimensions=dims + [dims[0]]))
        assert len(errors) == 1 and "'product' appears 2 times" in errors[0]

    def test_an_unknown_dimension_is_named(self):
        dims = self._record()["dimensions"]
        dims[0] = {**dims[0], "dimension": "ethics"}
        issues = self._issues(self._record(dimensions=dims))
        assert any("'ethics'" in i for i in issues) and any("'product' appears 0 times" in i for i in issues)

    @pytest.mark.parametrize("verdict", ["maybe", None, "Required"])
    def test_a_verdict_is_one_of_three(self, verdict):
        dims = self._record()["dimensions"]
        dims[3] = {**dims[3], "verdict": verdict}
        assert self._fields(self._record(dimensions=dims)) == ["impact_analysis.dimensions[3]"]

    @pytest.mark.parametrize("reason", ["", "  ", None])
    def test_a_dimension_needs_a_reason(self, reason):
        dims = self._record()["dimensions"]
        dims[0] = {**dims[0], "reason": reason}
        assert self._fields(self._record(dimensions=dims)) == ["impact_analysis.dimensions[0]"]

    def test_a_dimension_may_omit_items_but_not_make_them_a_string(self):
        dims = self._record()["dimensions"]
        del dims[0]["items"]
        assert self._fields(self._record(dimensions=dims)) == []
        dims[0]["items"] = "SRS-001"
        assert self._fields(self._record(dimensions=dims)) == ["impact_analysis.dimensions[0]"]

    def _issues(self, record) -> list[str]:
        from medharness.services.design_validation import impact_analysis_shape_errors

        return [e["issue"] for e in impact_analysis_shape_errors("CR-001", record)]
