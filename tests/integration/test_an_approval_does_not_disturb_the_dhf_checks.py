"""APPROVAL items sit outside every chain: `verify dhf` finds no coverage or placeholder problem in them."""

from __future__ import annotations

import json
from pathlib import Path

from fixtures.approvals import build_project
from fixtures.starter import keep_the_starter_text


def test_strict_verify_dhf_gives_the_same_answer_with_an_approval_on_file(tmp_path: Path) -> None:
    project = build_project(tmp_path)
    keep_the_starter_text(project.dhf)
    project.edit("SRS-001", content="Changed.")

    def strict() -> dict:
        result = project.run("verify", "dhf", "--strict")
        return json.loads(result.stdout.splitlines()[0])

    before = strict()
    assert project.approve("Lead").exit_code == 0
    after = strict()

    assert after["errors"] == before["errors"] and after["warnings"] == before["warnings"]
    assert not any("APR-001" in message for message in after["errors"] + after["warnings"])


def test_the_starter_dhf_ships_no_approval(tmp_path: Path) -> None:
    project = build_project(tmp_path, with_approvers=False)

    assert list((project.dhf / "items").rglob("APR-*")) == []
    assert project.run("item", "list", "--type", "APPROVAL").stdout == ""
