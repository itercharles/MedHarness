"""The branch must carry what the CR said it would change.

`--cr` used to reach only `details.cr_id`; the verdict came from "did any DHF
item change at all". That passes a branch which edited something unrelated, and
fails any PR without a CR — so the rule about when it applies had to live in
each adopter's workflow conditions rather than in the command.

`change plan` already writes `affected_items`. Comparing the promise to the diff
is the check the name always claimed.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from medharness.services.git import validate_atomic_branch

CHANGED = {"created": [], "updated": ["SRS-001"], "deleted": []}
NOTHING = {"created": [], "updated": [], "deleted": []}


def _run(tmp_path: Path, cr_item, dhf_changes=CHANGED):
    with patch("medharness.services.git.collect_dhf_item_changes", return_value=dhf_changes), \
         patch("dhfkit.local_adapter.LocalDHFAdapter") as adapter:
        adapter.return_value.get_item.return_value = cr_item
        adapter.return_value.list_items.return_value = []
        adapter.return_value.config = None
        with patch("medharness.services.traceability.find_affected_risks", return_value=[]):
            dhf = tmp_path / "DHF"
            dhf.mkdir(exist_ok=True)
            return validate_atomic_branch(tmp_path, dhf, "CR-001", since_ref="main")


class TestThePromiseIsChecked:
    def test_an_unchanged_promised_item_fails(self, tmp_path: Path) -> None:
        result = _run(tmp_path, {"id": "CR-001", "affected_items": ["SRS-001", "SYS-001"]})
        assert result["passed"] is False
        assert "SYS-001" in " ".join(result["errors"])
        assert result["details"]["promised_but_unchanged"] == ["SYS-001"]

    def test_keeping_the_promise_passes(self, tmp_path: Path) -> None:
        result = _run(tmp_path, {"id": "CR-001", "affected_items": ["SRS-001"]})
        assert result["passed"] is True, result["errors"]

    def test_changing_more_than_promised_is_not_a_failure(self, tmp_path: Path) -> None:
        """Touching an extra item is not what this gate is for."""
        result = _run(
            tmp_path,
            {"id": "CR-001", "affected_items": ["SRS-001"]},
            {"created": [], "updated": ["SRS-001", "SWDD-009"], "deleted": []},
        )
        assert result["passed"] is True, result["errors"]


class TestWhenThereIsNothingToCheckAgainst:
    def test_a_cr_with_no_affected_items_and_no_changes_fails(self, tmp_path: Path) -> None:
        result = _run(tmp_path, {"id": "CR-001", "affected_items": []}, NOTHING)
        assert result["passed"] is False
        assert "no affected_items" in " ".join(result["errors"])

    def test_a_missing_cr_does_not_fail_the_branch(self, tmp_path: Path) -> None:
        """A PR with no CR is not this gate's business."""
        result = _run(tmp_path, None, NOTHING)
        assert result["passed"] is True, (
            "a branch with no CR failed; the old rule forced every adopter to "
            "guard this command with workflow conditions"
        )
        assert result["details"]["cr_found"] is False
