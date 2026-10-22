"""An approval made with a key the list marks `no_touch_required` is valid, and says it was made without proven presence."""

from __future__ import annotations

from pathlib import Path

import yaml
from fixtures.approvals import build_project


def test_a_valid_approval_from_a_no_touch_key_warns(tmp_path: Path) -> None:
    project = build_project(tmp_path)
    project.edit("SRS-001", content="Changed.")
    project.approve("Lead")

    answer = project.verify()

    assert answer["passed"] is True
    assert answer["warnings"] == ["APR-001 was signed with a key marked no_touch_required: made without proven presence."]


def test_a_key_that_proves_presence_leaves_no_warning(tmp_path: Path) -> None:
    project = build_project(tmp_path)
    entries = yaml.safe_load(project.approvers_file.read_text())
    entries[0]["no_touch_required"] = False
    project.write_approvers(entries)
    project.edit("SRS-001", content="Changed.")
    project.approve("Lead")
    # The list changed on the branch too; approve it so only presence is in question.
    project.approve("Lead", "--approvers")

    answer = project.verify()

    assert answer["passed"] is True, answer["errors"]
    assert answer["warnings"] == []
