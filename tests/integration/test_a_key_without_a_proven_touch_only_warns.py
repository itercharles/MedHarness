"""A signature made with a key the list marks `no_touch_required` is valid, and says it was made without proven presence."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from fixtures.approvals import build_project


@pytest.mark.dhf_links("SRS-064")
@pytest.mark.dhf_testing("T2")
def test_a_valid_signature_from_a_no_touch_key_warns(tmp_path: Path) -> None:
    project = build_project(tmp_path)
    project.ready_to_release()
    project.release()
    project.sign("Lead")

    answer = project.verify()

    assert answer["passed"] is True
    assert answer["warnings"] == [f"{project.records()[0].stem} was signed with a key marked no_touch_required: made without proven presence."]


@pytest.mark.dhf_links("SRS-064")
@pytest.mark.dhf_testing("T3")
def test_a_key_that_proves_presence_leaves_no_warning(tmp_path: Path) -> None:
    project = build_project(tmp_path)
    entries = yaml.safe_load(project.approvers_file.read_text())
    entries[0]["no_touch_required"] = False
    project.write_approvers(entries)
    project.ready_to_release()
    project.release()
    project.sign("Lead")
    # The list changed on the branch too; approve it so only presence is in question.
    project.approve("Lead", "--approvers")

    answer = project.verify()

    assert answer["passed"] is True, answer["errors"]
    assert answer["warnings"] == []
