"""`build plan` must find the CR it works on in the DHF.

A CR that cannot be read or is missing stops the run before any model is asked to
write items against it. Triage is not checked here: a rejected CR is recorded by the
prompt and left alone, and an accepted one needs no record of its own.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from medharness.services.design_validation import _check_cr_workflow_fields


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


class TestTheCrItem:
    def test_a_cr_with_no_triage_result_reports_nothing(self) -> None:
        assert _fields({"id": "CR-001"}) == []

    def test_a_cr_triage_rejected_is_left_alone(self) -> None:
        """Rejection stops at Step 2 and produces no cascade."""
        assert _fields({"id": "CR-001", "triage_result": {"verdict": "rejected", "notes": "duplicate"}}) == []

    def test_a_missing_cr_is_reported_as_that(self) -> None:
        assert _fields(None) == ["cr_item"]

    def test_an_unreadable_dhf_is_reported_not_swallowed(self) -> None:
        errors = _check(error=OSError("disk gone"))
        assert [e["field"] for e in errors] == ["cr_item"]
        assert "disk gone" in errors[0]["issue"]
