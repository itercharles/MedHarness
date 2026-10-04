"""`build plan` must not report success without the fields closure requires.

`triage_result` is written by nothing but the prompt: the LLM is told to run
`medharness item update`, and no code checked that it did. A run that skipped Step 2
reported `outcome: ok`, and the omission surfaced at `verify completion`.

Checked in the validator rather than after it, so the fix pass corrects it in
the same run instead of failing a CR weeks later.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from medharness.services.design_validation import _check_cr_workflow_fields

APPROVED = {"verdict": "approved", "complexity": "small"}


def _check(cr_item: dict | None = None, error: Exception | None = None) -> list[dict]:
    store = MagicMock()
    if error:
        store.get_item.side_effect = error
    else:
        store.get_item.return_value = cr_item
    with patch("medharness.services.design_validation.open_store", return_value=store):
        return _check_cr_workflow_fields(Path("DHF"), "CR-001")


def _fields(cr_item: dict | None) -> list[str]:
    return [e["field"] for e in _check(cr_item)]


class TestWhatStepOneLeavesBehind:
    def test_a_missing_triage_result_is_reported(self) -> None:
        assert "triage_result" in _fields({"id": "CR-001"})

    def test_a_complete_cr_reports_nothing(self) -> None:
        assert _fields({"id": "CR-001", "triage_result": APPROVED}) == []

    def test_an_unapproved_verdict_is_not_a_triage_result(self) -> None:
        assert "triage_result" in _fields(
            {"id": "CR-001", "triage_result": {"verdict": "needs_info"}}
        )

    def test_a_non_dict_triage_result_is_not_one(self) -> None:
        assert "triage_result" in _fields(
            {"id": "CR-001", "triage_result": "approved"}
        )


class TestWhenTheChecksDoNotApply:
    def test_a_rejected_cr_is_left_alone(self) -> None:
        """Rejection stops at Step 2 and produces no cascade."""
        assert _fields({"id": "CR-001", "status": "rejected"}) == []

    def test_a_missing_cr_is_reported_as_that(self) -> None:
        assert _fields(None) == ["cr_item"]

    def test_an_unreadable_dhf_is_reported_not_swallowed(self) -> None:
        errors = _check(error=OSError("disk gone"))
        assert [e["field"] for e in errors] == ["cr_item"]
        assert "disk gone" in errors[0]["issue"]


class TestTheMessageIsActionable:
    """These errors are fed back to the model as the fix prompt."""

    @pytest.mark.parametrize("field", ["triage_result"])
    def test_the_fix_names_the_command_to_run(self, field: str) -> None:
        errors = _check({"id": "CR-001"})
        fix = next(e["fix"] for e in errors if e["field"] == field)
        assert "medharness" in fix and "item update" in fix and field in fix


class TestAgainstARealDhf:
    def test_the_validator_catches_a_plan_that_skipped_both_steps(self, tmp_path: Path) -> None:
        import subprocess
        import sys

        from medharness.services.design_validation import validate_generate_dhf

        subprocess.run([sys.executable, "-c", "from medharness.cli import main; main()", "init"],
                       cwd=tmp_path, capture_output=True, check=False)
        dhf = tmp_path / "DHF"
        if not (dhf / "config" / "global.yaml").exists():
            pytest.skip("scaffold unavailable")

        cr = dhf / "items" / "07_cr" / "CR-001.yaml"
        cr.write_text(cr.read_text() + "implementation_notes: planned\naffected_risk_items: []\n",
                      encoding="utf-8")

        errors = validate_generate_dhf(
            "CR-001", dhf, {"created": [], "updated": ["CR-001"], "deleted": []},
        )
        fields = [e["field"] for e in errors]
        assert "triage_result" in fields, (
            "the cascade is complete and the only thing missing is what Step 2 "
            "and Step 6 write; the validator reported none of it"
        )
