"""Tests for atomic branch validation.

`judge_branch` is the decision and takes the change sets and the CR as values;
`validate_atomic_branch` only reads them from git and the DHF.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from medharness.services.git import judge_branch, validate_atomic_branch

NOTHING = {"created": [], "updated": [], "deleted": []}


def test_code_and_dhf_changes_pass() -> None:
    result = judge_branch(
        "CR-001", None,
        {"created": ["SRS-010"], "updated": ["SYS-001"], "deleted": []},
        {"created": [], "updated": ["src/app.py"], "deleted": []},
        code_paths=("src/",),
    )

    assert result["passed"] is True
    assert result["details"]["findings"] == []
    assert result["details"]["cr_found"] is False


def test_no_code_changes_fail_when_code_paths_are_given() -> None:
    result = judge_branch("CR-001", None, NOTHING, NOTHING, code_paths=("src/",))

    assert result["passed"] is False
    assert any(e["field"] == "code_branch" for e in result["details"]["findings"])


def test_without_code_paths_code_is_not_checked() -> None:
    result = judge_branch(
        "CR-001", None, {"created": ["SRS-010"], "updated": [], "deleted": []}, NOTHING,
    )

    assert result["passed"] is True
    assert result["details"]["findings"] == []


def test_a_cr_with_nothing_promised_and_nothing_changed_fails() -> None:
    """The old rule was "every CR branch must change the DHF". That fails any PR
    with no CR, which is why adopters had to guard this command with workflow
    conditions. It now checks the CR's own affected_items; the blanket case
    survives only when a CR exists and promised nothing."""
    result = judge_branch("CR-001", {"id": "CR-001", "affected_items": []}, NOTHING, NOTHING)

    assert result["passed"] is False
    assert any(e["field"] == "dhf_branch" for e in result["details"]["findings"])


def test_validate_reads_the_diff_and_the_cr_it_judges(tmp_path: Path) -> None:
    dhf = tmp_path / "DHF"
    dhf.mkdir()

    with patch("medharness.services.git.collect_dhf_item_changes",
               return_value={"created": [], "updated": ["SYS-001"], "deleted": []}) as items, \
         patch("medharness.services.git.collect_path_changes", return_value=NOTHING) as paths, \
         patch("dhfkit.local_adapter.LocalDHFAdapter") as adapter:
        adapter.return_value.get_item.return_value = {"id": "CR-001", "affected_items": ["SRS-001"]}
        result = validate_atomic_branch(tmp_path, dhf, "CR-001", since_ref="main",
                                        code_paths=("src/",))

    items.assert_called_once_with(tmp_path, "main")
    paths.assert_called_once_with(tmp_path, "main", "src/")
    adapter.assert_called_once_with(dhf)
    assert {e["field"] for e in result["details"]["findings"]} == {"code_branch", "dhf_branch"}
    assert result["details"]["promised_but_unchanged"] == ["SRS-001"]
