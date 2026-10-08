"""The branch must carry what the CR said it would change.

`--cr` used to reach only `details.cr_id`; the verdict came from "did any DHF
item change at all". That passes a branch which edited something unrelated, and
fails any PR without a CR — so the rule about when it applies had to live in
each adopter's workflow conditions rather than in the command.

`build plan` already writes `affected_items`. Comparing the promise to the diff
is the check the name always claimed.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from medharness.services.verify_changes import judge_branch, validate_atomic_branch

CHANGED = {"created": [], "updated": ["SRS-001"], "deleted": []}
NOTHING = {"created": [], "updated": [], "deleted": []}


def _run(cr_item, dhf_changes=CHANGED):
    return judge_branch("CR-001", cr_item, dhf_changes, NOTHING, since_ref="main")


class TestThePromiseIsChecked:
    def test_an_unchanged_promised_item_fails(self) -> None:
        result = _run({"id": "CR-001", "affected_items": ["SRS-001", "SYS-001"]})
        assert result["passed"] is False
        assert "SYS-001" in " ".join(result["errors"])
        assert result["details"]["promised_but_unchanged"] == ["SYS-001"]

    def test_keeping_the_promise_passes(self) -> None:
        result = _run({"id": "CR-001", "affected_items": ["SRS-001"]})
        assert result["passed"] is True, result["errors"]

    def test_changing_an_item_the_cr_does_not_list_fails(self) -> None:
        """Nothing else records it: `verify completion` checks only what is listed."""
        result = _run(
            {"id": "CR-001", "affected_items": ["SRS-001"]},
            {"created": [], "updated": ["SRS-001", "SWDD-009"], "deleted": []},
        )
        assert result["passed"] is False
        assert "SWDD-009" in " ".join(result["errors"])

    def test_the_cr_itself_need_not_list_itself(self) -> None:
        result = _run(
            {"id": "CR-001", "affected_items": ["SRS-001"]},
            {"created": [], "updated": ["SRS-001", "CR-001"], "deleted": []},
        )
        assert result["passed"] is True, result["errors"]


class TestWhenThereIsNothingToCheckAgainst:
    def test_a_cr_with_no_affected_items_and_no_changes_fails(self) -> None:
        result = _run({"id": "CR-001", "affected_items": []}, NOTHING)
        assert result["passed"] is False
        assert "no affected_items" in " ".join(result["errors"])

    def test_a_missing_cr_does_not_fail_the_branch(self) -> None:
        """A PR with no CR is not this gate's business."""
        result = _run(None, NOTHING)
        assert result["passed"] is True, (
            "a branch with no CR failed; the old rule forced every adopter to "
            "guard this command with workflow conditions"
        )
        assert result["details"]["cr_found"] is False


class TestAgainstARealChangeSet:
    """Inline, populated change sets.

    `test_cr_does_not_affect_itself` counts these: a CR can only appear in its
    own change set when that set is not empty, and the suite once drove the
    empty case almost everywhere. Shared constants are invisible to that count,
    so these spell the dict out.
    """

    def test_a_promise_kept_across_several_changed_items(self, tmp_path: Path) -> None:
        with patch("medharness.services.git.collect_dhf_item_changes",
                   return_value={"created": ["SWDD-007"], "updated": ["SRS-001", "SYS-001"],
                                 "deleted": []}), \
             patch("dhfkit.item_store.ItemStore") as adapter:
            adapter.return_value.config.impact_depth = 0   # these judge the promise, not the impact
            adapter.return_value.get_item.return_value = {
                "id": "CR-001", "affected_items": ["SRS-001", "SYS-001", "SWDD-007"],
            }
            dhf = tmp_path / "DHF"
            dhf.mkdir(exist_ok=True)
            result = validate_atomic_branch(tmp_path, dhf, "CR-001", since_ref="main")
        assert result["passed"] is True, result["errors"]

    def test_a_deleted_item_still_counts_as_changed(self, tmp_path: Path) -> None:
        """Retiring an item is how a CR keeps a promise to change it."""
        with patch("medharness.services.git.collect_dhf_item_changes",
                   return_value={"created": [], "updated": ["SRS-002"],
                                 "deleted": ["SRS-001"]}), \
             patch("dhfkit.item_store.ItemStore") as adapter:
            adapter.return_value.config.impact_depth = 0   # these judge the promise, not the impact
            adapter.return_value.get_item.return_value = {
                "id": "CR-001", "affected_items": ["SRS-001", "SRS-002"],
            }
            dhf = tmp_path / "DHF"
            dhf.mkdir(exist_ok=True)
            result = validate_atomic_branch(tmp_path, dhf, "CR-001", since_ref="main")
        assert result["passed"] is True, result["errors"]


class TestCouldNotCheckIsNotABrokenPromise:
    """A repo with no remote could not diff, and was told its CR broke a promise.

    `collect_path_changes` returned three empty lists for "git failed" and for
    "nothing changed" alike. With a CR that promised nothing, that read as "run
    `build plan`" — the wrong failure with the wrong fix.
    """

    def _unreadable(self, tmp_path: Path, cr_item):
        from medharness.services.git import DiffUnavailable

        with patch("medharness.services.git.collect_dhf_item_changes",
                   side_effect=DiffUnavailable("fatal: bad revision 'origin/main'")), \
             patch("dhfkit.item_store.ItemStore") as adapter:
            adapter.return_value.config.impact_depth = 0   # these judge the promise, not the impact
            adapter.return_value.get_item.return_value = cr_item
            dhf = tmp_path / "DHF"
            dhf.mkdir(exist_ok=True)
            return validate_atomic_branch(tmp_path, dhf, "CR-001")

    @pytest.mark.parametrize("cr_item", [
        {"id": "CR-001"},
        {"id": "CR-001", "affected_items": ["SYS-001"]},
    ], ids=["promised nothing", "promised SYS-001"])
    def test_it_says_it_could_not_read_the_diff(self, tmp_path: Path, cr_item) -> None:
        result = self._unreadable(tmp_path, cr_item)
        assert result["passed"] is False
        assert result["errors"] == [
            "diff_unavailable: Could not diff against origin/main: "
            "fatal: bad revision 'origin/main'."
        ], result["errors"]

    def test_it_does_not_accuse_the_cr(self, tmp_path: Path) -> None:
        result = self._unreadable(tmp_path, {"id": "CR-001", "affected_items": ["SYS-001"]})
        joined = " ".join(result["errors"])
        assert "dhf_branch" not in joined and "build plan" not in joined, joined
