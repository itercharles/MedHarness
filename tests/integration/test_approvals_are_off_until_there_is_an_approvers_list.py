"""Without `DHF/config/approvers.yaml` nothing about approvals changes for a project."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fixtures.approvals import build_project


@pytest.mark.dhf_links("SRS-063")
@pytest.mark.dhf_testing("T1")
def test_a_project_without_an_approvers_list_passes_untouched(tmp_path: Path) -> None:
    project = build_project(tmp_path, with_approvers=False)
    project.ready_to_release()
    project.release()

    answer = project.verify()

    assert answer["passed"] is True
    assert "not configured" in answer["summary"]


def test_approving_without_an_approvers_list_says_how_to_turn_it_on(tmp_path: Path) -> None:
    project = build_project(tmp_path, with_approvers=False)

    result = project.sign("Lead")

    assert result.exit_code == 1
    assert "approvers.yaml" in result.stderr


@pytest.mark.dhf_links("SRS-022")
@pytest.mark.dhf_testing("T5")
def test_deleting_the_approvers_list_does_not_switch_approvals_off(tmp_path: Path) -> None:
    project = build_project(tmp_path)
    project.approvers_file.unlink()

    answer = project.verify()

    assert answer["passed"] is False
    assert "approvers.yaml" in answer["errors"][0]


@pytest.mark.dhf_links("SRS-022")
@pytest.mark.dhf_testing("T6")
def test_a_malformed_approvers_list_is_named_not_crashed_on(tmp_path: Path) -> None:
    project = build_project(tmp_path)
    project.approvers_file.write_text("name: Lead\n", encoding="utf-8")

    answer = project.verify()

    assert answer["passed"] is False
    assert "must be a list of approvers" in answer["errors"][0]


def _verify_against(project, ref: str) -> dict:
    result = project.run("verify", "approval", "--since-ref", ref)
    return json.loads(result.stdout.splitlines()[0])


@pytest.mark.dhf_links("SRS-022")
@pytest.mark.dhf_testing("T5")
def test_deleting_the_list_is_refused_even_when_the_reference_cannot_be_reached(tmp_path: Path) -> None:
    """A branch could delete the list and name a reference no one can fetch, so the gate looked at nothing."""
    project = build_project(tmp_path)
    project.approvers_file.unlink()

    answer = _verify_against(project, "origin/nowhere")

    assert answer["passed"] is False
    assert "existed on this branch" in answer["errors"][0] and "approvers.yaml" in answer["errors"][0]


@pytest.mark.dhf_links("SRS-063")
@pytest.mark.dhf_testing("T1")
def test_a_project_that_never_had_a_list_still_passes_when_the_reference_cannot_be_reached(tmp_path: Path) -> None:
    project = build_project(tmp_path, with_approvers=False)

    answer = _verify_against(project, "origin/nowhere")

    assert answer["passed"] is True
    assert "not configured" in answer["summary"]
