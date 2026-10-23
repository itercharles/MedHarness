"""Approval records are not items: `verify dhf` and `item list` know nothing about them."""

from __future__ import annotations

import json
from pathlib import Path

from fixtures.approvals import build_project


def test_strict_verify_dhf_gives_the_same_answer_with_an_approval_on_file(tmp_path: Path) -> None:
    project = build_project(tmp_path)
    project.ready_to_release()
    project.release()

    def strict() -> dict:
        result = project.run("verify", "dhf", "--strict")
        return json.loads(result.stdout.splitlines()[0])

    before = strict()
    assert project.sign("Lead").exit_code == 0
    after = strict()

    assert after["errors"] == before["errors"] and after["warnings"] == before["warnings"]
    assert project.records() and not any(project.records()[0].stem in m for m in after["errors"] + after["warnings"])


def test_the_starter_dhf_ships_no_approval(tmp_path: Path) -> None:
    project = build_project(tmp_path, with_approvers=False)

    assert not (project.dhf / "approvals").exists()


def test_item_list_does_not_show_approval_records(tmp_path: Path) -> None:
    project = build_project(tmp_path)
    project.ready_to_release()
    project.release()
    before = project.run("item", "list").stdout
    assert project.sign("Lead").exit_code == 0
    uid = project.records()[0].stem

    result = project.run("item", "list")

    assert result.stdout == before
    assert uid not in result.stdout
    assert project.run("item", "get", uid).exit_code != 0
