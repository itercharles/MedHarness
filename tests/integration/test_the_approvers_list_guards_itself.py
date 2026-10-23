"""A change to `approvers.yaml` is approved by someone on the list as it was where the branch left the base."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from fixtures.approvals import Project, build_project, entry, make_key


@pytest.fixture
def project(tmp_path: Path) -> Project:
    return build_project(tmp_path)


def _add_mallory(project: Project) -> None:
    entries = yaml.safe_load(project.approvers_file.read_text())
    entries.append(entry("Mallory", project.keys["Mallory"], ["software-lead", "ccb"]))
    project.write_approvers(entries)


def test_adding_a_key_without_an_approval_from_the_old_list_fails(project: Project) -> None:
    _add_mallory(project)

    answer = project.verify()

    assert answer["passed"] is False
    assert "approvers.yaml changed" in answer["errors"][0]
    assert "Lead, Pat, Sam, Quinn" in answer["errors"][0]


def test_an_added_key_cannot_approve_its_own_addition(project: Project) -> None:
    _add_mallory(project)
    assert project.approve("Mallory", "--approvers").exit_code == 0

    answer = project.verify()

    assert answer["passed"] is False
    assert "approvers.yaml changed" in answer["errors"][0]


def test_adding_a_key_with_an_approval_from_the_old_list_passes(project: Project) -> None:
    _add_mallory(project)
    result = project.approve("Lead", "--approvers")
    assert result.exit_code == 0, result.stderr

    assert project.verify()["passed"] is True


def test_editing_the_list_after_it_was_approved_makes_that_approval_stale(project: Project) -> None:
    _add_mallory(project)
    project.approve("Lead", "--approvers")
    entries = yaml.safe_load(project.approvers_file.read_text())
    entries[2]["roles"].append("quality-lead")
    project.write_approvers(entries)

    assert project.verify()["passed"] is False


def test_the_first_approvers_list_is_accepted_as_the_root_of_trust(tmp_path: Path) -> None:
    project = build_project(tmp_path, with_approvers=False)
    project.write_approvers([entry("Lead", project.keys["Lead"], ["software-lead"])])

    answer = project.verify()

    assert answer["passed"] is True
    assert any("root of trust" in w for w in answer["warnings"])


def test_a_new_key_on_an_unrelated_name_does_not_stand_in_for_the_old_list(project: Project) -> None:
    other = make_key(project.keys["Lead"].parent, "Other")
    project.keys["Other"] = other
    entries = yaml.safe_load(project.approvers_file.read_text())
    entries.append(entry("Other", other, ["ccb"]))
    project.write_approvers(entries)
    project.approve("Other", "--approvers")

    assert project.verify()["passed"] is False
